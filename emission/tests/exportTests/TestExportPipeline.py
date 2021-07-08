from future import standard_library
standard_library.install_aliases()
from builtins import *
import os
import unittest
import json
import bson.json_util as bju
import pathlib as pl
import emission.storage.timeseries.abstract_timeseries as esta
import gzip
import emission.tests.common as etc
import emission.pipeline.export_stage as epe
import emission.storage.pipeline_queries as espq
import emission.exportdata.export_data as eeed
import emission.export.export as eee

class TestExportPipeline(unittest.TestCase):
    def testExportPipeline(self):
        #Setup
        etc.setupRealExample(self, "emission/tests/data/real_examples/shankari_2015-07-22") #is this needed? thinking yes
        etc.runIntakePipeline(self.testUUID)

        ts = esta.TimeSeries.get_time_series(self.testUUID)
        time_query = espq.get_time_range_for_export_data(self.testUUID)
        file_name = os.environ.get('DATA_DIR', 'emission/archived/') + "archive_%s_%s_%s" % (self.testUUID, time_query.startTs, time_query.endTs)

        eee.export(self.testUUID, ts, time_query.startTs, time_query.endTs, file_name, False)
        file_name += ".gz"

        #Assert the file exists after the export process
        self.assertTrue(pl.Path(file_name).is_file()) 
        with gzip.open(file_name, 'r') as ef:
            exported_data = json.loads(ef.read().decode('utf-8'))
            
        confirmed_trips_exported = []
        for t in exported_data:
            if t['metadata']['key'] == "analysis/confirmed_trip":
                confirmed_trips_exported.append(t)
        raw_data = self.readDataFromFile("emission/tests/data/real_examples/shankari_2015-07-22")
        confirmed_trips_raw = []
        for t in raw_data:
            if t['metadata']['key'] == "analysis/confirmed_trip":
                confirmed_trips_raw.append(t)
        confirmed_trips_db = list(ts.find_entries(["analysis/confirmed_trip"], None))

        #Testing the matching total number of confirmed trips, testing no confirmed trips in raw.
        #Testing also for the first three trips that the object ids and user ids are consistent.
        self.assertEqual(len(confirmed_trips_exported), len(confirmed_trips_db))
        self.assertEqual([], confirmed_trips_raw)
        self.assertEqual(str(confirmed_trips_db[0]['_id']),confirmed_trips_exported[0]['_id']['$oid'])
        self.assertEqual(str(confirmed_trips_db[1]['_id']),confirmed_trips_exported[1]['_id']['$oid'])
        self.assertEqual(str(confirmed_trips_db[2]['_id']),confirmed_trips_exported[2]['_id']['$oid'])
        self.assertEqual(str(confirmed_trips_db[0]['user_id']).replace("-", ""),confirmed_trips_exported[0]['user_id']['$uuid'])
        self.assertEqual(str(confirmed_trips_db[1]['user_id']).replace("-", ""),confirmed_trips_exported[1]['user_id']['$uuid'])
        self.assertEqual(str(confirmed_trips_db[2]['user_id']).replace("-", ""),confirmed_trips_exported[2]['user_id']['$uuid'])

        #Testing to confirm the length of data entries, should be the same for raw and processed
        background_location_exported = []
        for t in exported_data:
            if t['metadata']['key'] == "background/location":
                background_location_exported.append(t)
        background_location_raw = []
        for t in raw_data:
            if t['metadata']['key'] == "background/location":
                background_location_raw.append(t)
        background_location_db = list(ts.find_entries(["background/location"], None))
        self.assertEqual(len(background_location_exported), len(background_location_raw))
        self.assertEqual(len(background_location_exported), len(background_location_db))
 
    def readDataFromFile(self, dataFile):
        with open(dataFile) as dect:
            raw_data = json.load(dect, object_hook = bju.object_hook)
            return raw_data


if __name__ == '__main__':
     etc.configLogging()
     unittest.main()
