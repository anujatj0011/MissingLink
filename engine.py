"""Scheduled transfer analysis; all time values are seconds since service-day start."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import pandas as pd


def seconds(value):
    if pd.isna(value) or not str(value).strip():
        return np.nan
    h, m, s = map(int, str(value).split(':'))
    if h < 0 or not 0 <= m < 60 or not 0 <= s < 60:
        raise ValueError(f'Invalid GTFS time: {value}')
    return h * 3600 + m * 60 + s


def clock(value):
    if pd.isna(value):
        return 'No service'
    value = int(value)
    return f'{value // 3600:02d}:{value % 3600 // 60:02d}'


def active_services(calendar, exceptions, day):
    stamp = day.strftime('%Y%m%d')
    active = set()
    if not calendar.empty:
        weekday = day.strftime('%A').lower()
        mask = (calendar.start_date <= stamp) & (calendar.end_date >= stamp) & (calendar[weekday] == '1')
        active.update(calendar.loc[mask, 'service_id'])
    if not exceptions.empty:
        for row in exceptions[exceptions.date == stamp].itertuples():
            if row.exception_type == '1':
                active.add(row.service_id)
            elif row.exception_type == '2':
                active.discard(row.service_id)
    return active


def load_gtfs(data, day):
    """Read a ZIP without extracting it; filter stops/trips before reading stop times."""
    warnings = []
    source = data if isinstance(data, (str, Path)) else BytesIO(data)
    with ZipFile(source) as archive:
        members = {n.rsplit('/', 1)[-1]: n for n in archive.namelist() if not n.endswith('/')}
        def read(name, required=True):
            if name not in members:
                if required:
                    raise ValueError(f'Missing {name}')
                return pd.DataFrame()
            return pd.read_csv(archive.open(members[name]), dtype=str, keep_default_na=False)
        stops, routes, trips = read('stops.txt'), read('routes.txt'), read('trips.txt')
        cal, exceptions = read('calendar.txt', False), read('calendar_dates.txt', False)
        if cal.empty and exceptions.empty:
            raise ValueError('Provide calendar.txt or calendar_dates.txt for service-date filtering.')
        active = active_services(cal, exceptions, day)
        trips = trips[trips.service_id.isin(active)].copy()
        if 'direction_id' not in trips:
            trips['direction_id'] = '?'
        trips['direction_id'] = trips.direction_id.replace('', '?')
        if 'trip_headsign' not in trips:
            trips['trip_headsign'] = ''
        freq = read('frequencies.txt', False)
        if not freq.empty:
            excluded = set(freq.trip_id) & set(trips.trip_id)
            trips = trips[~trips.trip_id.isin(excluded)]
            warnings.append(f'Excluded {len(excluded)} frequency-based trips: expansion is outside this prototype.')
        stops['stop_lat'] = pd.to_numeric(stops.stop_lat, errors='coerce')
        stops['stop_lon'] = pd.to_numeric(stops.stop_lon, errors='coerce')
        # Approximate Dublin-region bounding box; explicit in the UI.
        stops = stops[stops.stop_lat.between(53.18, 53.46) & stops.stop_lon.between(-6.50, -6.02)].copy()
        if 'location_type' in stops:
            stops = stops[stops.location_type.isin(['', '0'])]
        if 'stop_times.txt' not in members:
            raise ValueError('Missing stop_times.txt')
        chunks = []
        skipped = 0
        for chunk in pd.read_csv(archive.open(members['stop_times.txt']), dtype=str, keep_default_na=False, chunksize=200000):
            chunk = chunk[chunk.stop_id.isin(stops.stop_id) & chunk.trip_id.isin(trips.trip_id)].copy()
            for col in ['pickup_type', 'drop_off_type']:
                if col not in chunk:
                    chunk[col] = '0'
                chunk[col] = chunk[col].replace('', '0')
            chunk['arrival'] = chunk.arrival_time.map(seconds)
            chunk['departure'] = chunk.departure_time.map(seconds)
            missing = chunk.arrival.isna() | chunk.departure.isna()
            skipped += int(missing.sum())
            chunks.append(chunk[~missing])
        if skipped:
            warnings.append(f'Skipped {skipped} stop-time rows with unspecified times; no interpolation is assumed.')
        if not chunks:
            raise ValueError('No stop times found.')
        events = pd.concat(chunks, ignore_index=True).merge(trips[['trip_id', 'route_id', 'direction_id', 'trip_headsign']], on='trip_id')
        if 'route_short_name' not in routes:
            routes['route_short_name'] = ''
        if 'route_long_name' not in routes:
            routes['route_long_name'] = ''
        routes['label'] = routes.route_short_name.where(routes.route_short_name != '', routes.route_long_name)
        routes['label'] = routes.label.where(routes.label != '', routes.route_id)
        events = events.merge(routes[['route_id', 'label']], on='route_id')
        events['group'] = events.route_id + ' | ' + events.direction_id
        events['service'] = events.label + ' · direction ' + events.direction_id
        return stops, events, warnings


def match(arrivals, departures, buffer_minutes=2, shift_minutes=0):
    a = np.sort(np.asarray(arrivals, dtype=float))
    b = np.sort(np.unique(np.asarray(departures, dtype=float))) + shift_minutes * 60
    ready = a + buffer_minutes * 60
    idx = np.searchsorted(b, ready, side='left')
    prev_idx = np.searchsorted(b, ready, side='left') - 1
    nxt = np.full(len(a), np.nan)
    prev = np.full(len(a), np.nan)
    valid, has_prev = idx < len(b), prev_idx >= 0
    nxt[valid] = b[idx[valid]]
    prev[has_prev] = b[prev_idx[has_prev]]
    wait = (nxt - a) / 60
    miss = (ready - prev) / 60
    result = pd.DataFrame({'arrival': a, 'ready': ready, 'previous': prev, 'next': nxt,
                           'wait': wait, 'miss': miss, 'gap': (nxt-prev)/60})
    result['near_miss'] = result['miss'].between(1, 5) & (result.wait >= 15)
    return result


def metrics(transfers, departures):
    waits = transfers.wait.dropna()
    b = np.sort(np.unique(departures))
    headway = float(np.median(np.diff(b)) / 60) if len(b) > 1 else np.nan
    n = len(transfers)
    rate = float(transfers.near_miss.mean()) if n else 0
    median = float(waits.median()) if len(waits) else np.nan
    score = (40 * min(median/30, 1) + 30*rate + 20*min(headway/30, 1)) if np.isfinite(median) and np.isfinite(headway) else np.nan
    return dict(arrivals=n, matched=len(waits), no_service=n-len(waits), median=median,
                average=float(waits.mean()) if len(waits) else np.nan,
                p90=float(waits.quantile(.9)) if len(waits) else np.nan,
                over15=float((transfers.wait > 15).sum()/n) if n else 0,
                near_rate=rate, headway=headway, score=score,
                flagged=n >= 3 and rate >= .4)


def interchange_stops(stops, events):
    counts = events.groupby('stop_id').route_id.nunique()
    result = stops[stops.stop_id.isin(counts[counts >= 2].index)].copy()
    result['routes'] = result.stop_id.map(counts)
    return result.sort_values(['routes', 'stop_name'], ascending=[False, True])


def pair_data(events, stop_id, source, target, start, end):
    at = events[events.stop_id == stop_id]
    a = at[(at.group == source) & (at.drop_off_type == '0') & at.arrival.ge(start) & at.arrival.lt(end)]
    b = at[(at.group == target) & (at.pickup_type == '0')]
    # Retain connecting departures outside the arrival window to avoid boundary bias.
    return a.arrival.to_numpy(), b.departure.to_numpy()


def rank(stops, events, selected, start, end, buffer_minutes):
    rows = []
    names = stops.set_index('stop_id')
    for stop_id in selected:
        at = events[events.stop_id == stop_id]
        groups = at[['group', 'route_id', 'service']].drop_duplicates('group').set_index('group')
        for source in groups.index:
            for target in groups.index:
                if groups.loc[source, 'route_id'] == groups.loc[target, 'route_id']:
                    continue
                a, b = pair_data(at, stop_id, source, target, start, end)
                if not len(a) or not len(b):
                    continue
                transfers = match(a, b, buffer_minutes)
                row = metrics(transfers, b)
                rows.append(dict(stop_id=stop_id, location=names.loc[stop_id, 'stop_name'],
                                 source=source, target=target, connection=groups.loc[source, 'service'] + ' → ' + groups.loc[target, 'service'],
                                 lat=names.loc[stop_id, 'stop_lat'], lon=names.loc[stop_id, 'stop_lon'], **row))
    return pd.DataFrame(rows).sort_values('score', ascending=False, na_position='last') if rows else pd.DataFrame()

