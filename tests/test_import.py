import unittest
from io import BytesIO
from zipfile import ZipFile
from datetime import date
from engine import load_gtfs

class ImportTests(unittest.TestCase):
    def test_zip_calendar_geography_direction_and_permissions(self):
        files = {
            'stops.txt':'stop_id,stop_name,stop_lat,stop_lon\ns,Dublin,53.3,-6.2\nx,Outside,54,-7\n',
            'routes.txt':'route_id,route_short_name\na,A\nb,B\n',
            'trips.txt':'route_id,service_id,trip_id,direction_id\na,yes,t1,0\nb,no,t2,1\nb,extra,t3,1\n',
            'calendar.txt':'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nyes,1,0,0,0,0,0,0,20260101,20261231\nno,1,0,0,0,0,0,0,20260101,20261231\n',
            'calendar_dates.txt':'service_id,date,exception_type\nno,20261005,2\nextra,20261005,1\n',
            'stop_times.txt':'trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type\nt1,25:10:00,25:10:00,s,1,0,0\nt1,25:20:00,25:20:00,x,2,0,0\nt2,17:00:00,17:00:00,s,1,0,0\nt3,17:00:00,17:00:00,s,1,1,0\n'}
        buffer = BytesIO()
        with ZipFile(buffer,'w') as archive:
            for name,text in files.items():
                archive.writestr('feed/'+name,text)
        stops,events,warnings = load_gtfs(buffer.getvalue(),date(2026,10,5))
        self.assertEqual(stops.stop_id.tolist(),['s'])
        self.assertEqual(set(events.trip_id),{'t1','t3'})
        self.assertEqual(events.loc[events.trip_id=='t1','arrival'].iloc[0],90600)
        self.assertEqual(events.loc[events.trip_id=='t3','pickup_type'].iloc[0],'1')
        self.assertEqual(set(events.direction_id),{'0','1'})

if __name__ == '__main__':
    unittest.main()
