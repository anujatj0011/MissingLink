"""Analyse all same-stop Dublin interchanges in the included weekday snapshot."""
from pathlib import Path
import json
import time
import gzip
import pandas as pd
from engine import match, metrics

DATA = Path(__file__).parent / 'data'

def write_transfer_index(events,poor):
    lookup = {}
    selected = events[events.stop_id.isin(poor.stop_id)]
    for (sid,key),group in selected.groupby(['stop_id','group'],sort=False):
        lookup.setdefault(sid,{})[key] = {
            'arrivals':group.loc[group.drop_off_type=='0','arrival'].tolist(),
            'departures':group.loc[group.pickup_type=='0','departure'].tolist()}
    with gzip.open(DATA/'transfer-index.json.gz','wt',encoding='utf-8') as file:
        json.dump(lookup,file,separators=(',',':'))

def build():
    started = time.time()
    stops = pd.read_csv(DATA/'stops-20261005.csv.gz',dtype={'stop_id':str}).set_index('stop_id')
    strings = ['stop_id','trip_id','route_id','direction_id','trip_headsign','pickup_type','drop_off_type','group','service']
    events = pd.read_csv(DATA/'events-20261005.csv.gz',dtype={c:str for c in strings},keep_default_na=False)
    rows, scenarios = [], []
    analysed_stops = 0
    for sid,at in events.groupby('stop_id',sort=False):
        if at.route_id.nunique() < 2:
            continue
        analysed_stops += 1
        services = {}
        for key, group in at.groupby('group',sort=False):
            services[key] = {'route':group.route_id.iloc[0], 'label':group.service.iloc[0],
                             'arrivals':group.loc[group.drop_off_type=='0','arrival'].to_numpy(),
                             'departures':group.loc[group.pickup_type=='0','departure'].to_numpy(),
                             'destinations':', '.join(sorted(set(group.trip_headsign)-{''}))}
        stop = stops.loc[sid]
        for period,start,end in [('Morning',7*3600,10*3600),('Evening',16*3600,19*3600)]:
            for source,incoming in services.items():
                a = incoming['arrivals']
                a = a[(a>=start)&(a<end)]
                if len(a) < 3:
                    continue
                for target,outgoing in services.items():
                    b = outgoing['departures']
                    if incoming['route'] == outgoing['route'] or not len(b):
                        continue
                    base = match(a,b,2)
                    stats = metrics(base,b)
                    key = f'{sid}/{source}/{target}/{period}'
                    row = dict(id=key,stop_id=sid,location=stop.stop_name,lat=stop.stop_lat,lon=stop.stop_lon,
                               source=source,target=target,connection=incoming['label']+' → '+outgoing['label'],
                               incoming_destinations=incoming['destinations'],outgoing_destinations=outgoing['destinations'],
                               period=period,**stats)
                    if stats['flagged']:
                        options = []
                        for shift in range(11):
                            changed = match(a,b,2,shift)
                            metric = metrics(changed,b)
                            improved = int(((changed.wait < base.wait) | (base.wait.isna() & changed.wait.notna())).sum())
                            worsened = int(((changed.wait > base.wait) | (base.wait.notna() & changed.wait.isna())).sum())
                            options.append(dict(id=key,shift=shift,median=metric['median'],near_rate=metric['near_rate'],
                                                no_service=metric['no_service'],improved=improved,worsened=worsened))
                        best = min(options,key=lambda x:(x['no_service'],x['median'],x['worsened'],x['shift']))
                        row.update(best_shift=best['shift'],best_median=best['median'],saving=stats['median']-best['median'],
                                   improved=best['improved'],worsened=best['worsened'])
                        scenarios.extend(options)
                    rows.append(row)
    full = pd.DataFrame(rows)
    poor = full[full.flagged].sort_values(['saving','score'],ascending=False).reset_index(drop=True)
    full.to_csv(DATA/'all-connections.csv.gz',index=False)
    poor.to_csv(DATA/'poor-transfers.csv',index=False)
    write_transfer_index(events,poor)
    pd.DataFrame(scenarios).to_csv(DATA/'improvement-scenarios.csv',index=False)
    summary = dict(interchanges=analysed_stops,connections=len(full),poor_connections=len(poor),
                   improvement_connections=int((poor.saving>0).sum()),improvement_locations=int(poor.loc[poor.saving>0,'stop_id'].nunique()),
                   active_stop_events=len(events),elapsed_seconds=round(time.time()-started,1),
                   scope='Included weekday timetable; morning 07:00–10:00 and evening 16:00–19:00; same-stop transfers; 2-minute boarding buffer.')
    (DATA/'analysis-summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))

if __name__ == '__main__':
    build()
