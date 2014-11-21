import unittest
import json
from utils import load_database_json, purge_database_json
from clients.gamified import gamified
import logging
from get_database import get_db, get_mode_db, get_section_db
from datetime import datetime, timedelta

logging.basicConfig(level=logging.DEBUG)

class TestGamified(unittest.TestCase):
    def setUp(self):
        import tests.common
        from copy import copy

        self.testUsers = ["test@example.com", "best@example.com", "fest@example.com",
                      "rest@example.com", "nest@example.com"]
        self.serverName = 'localhost'

        # Sometimes, we may have entries left behind in the database if one of the tests failed
        # or threw an exception, so let us start by cleaning up all entries
        tests.common.dropAllCollections(get_db())
        self.ModesColl = get_mode_db()
        self.assertEquals(self.ModesColl.find().count(), 0)

        self.setupUserAndClient()

        load_database_json.loadTable(self.serverName, "Stage_Modes", "tests/data/modes.json")
        load_database_json.loadTable(self.serverName, "Stage_Sections", "tests/data/testCarbonFile")
        self.SectionsColl = get_section_db()

        self.walkExpect = 1057.2524056424411
        self.busExpect = 2162.668467546699
        self.busCarbon = 267.0/1609
        self.airCarbon = 217.0/1609
        self.driveCarbon = 278.0/1609
        self.busOptimalCarbon = 92.0/1609

        self.now = datetime.now()
        self.dayago = self.now - timedelta(days=1)
        self.weekago = self.now - timedelta(weeks = 1)

        for section in self.SectionsColl.find():
            section['section_start_datetime'] = self.dayago
            section['section_end_datetime'] = self.dayago + timedelta(hours = 1)
            section['predicted_mode'] = {'walking': 1.0}
            if section['user_id'] == 'fest@example.com':
                logging.debug("Setting user_id for section %s, %s = %s" %
                    (section['trip_id'], section['section_id'], self.user.uuid))
                section['user_id'] = self.user.uuid
            if section['confirmed_mode'] == 5:
                airSection = copy(section)
                airSection['confirmed_mode'] = 9
                airSection['_id'] = section['_id'] + "_air"
                self.SectionsColl.insert(airSection)
                airSection['confirmed_mode'] = ''
                airSection['_id'] = section['_id'] + "_unconf"
                self.SectionsColl.insert(airSection)
          
            # print("Section start = %s, section end = %s" %
            #   (section['section_start_datetime'], section['section_end_datetime']))
            self.SectionsColl.save(section)

    def setupUserAndClient(self):
        # At this point, the more important test is to execute the query and see
        # how well it works
        from dao.user import User
        from dao.client import Client
        import tests.common
        from datetime import datetime, timedelta
        from get_database import get_section_db

        fakeEmail = "fest@example.com"

        client = Client("gamified")
        client.update(createKey = False)
        tests.common.makeValid(client)

        (resultPre, resultReg) = client.preRegister("this_is_the_super_secret_id", fakeEmail)
        studyList = Client.getPendingClientRegs(fakeEmail)
        self.assertEqual(studyList, ["gamified"])

        user = User.register("fest@example.com")
        self.assertEqual(user.getFirstStudy(), 'gamified')
        self.user = user

    def testGetScoreComponents(self):
        components = gamified.getScoreComponents(self.user.uuid, self.weekago, self.now)
        self.assertEqual(components[0], 0.75)
        # bus_short disappears in optimal, air_short disappears as long motorized, so optimal = 0
        # self.assertEqual(components[1], (self.busExpect * self.busCarbon) / 1000)
        # TODO: Figure out what we should do when optimal == 0. Currently, we
        # return 0, which seems sub-optimal (pun intended)
        self.assertEqual(components[1], 0.0)
        # air_short disappears as long motorized, but we need to consider walking
        allDrive = (self.busExpect * self.driveCarbon + self.walkExpect * self.driveCarbon)/1000
        myFootprint = (self.busExpect * self.busCarbon)/1000
        self.assertAlmostEqual(components[2], (allDrive - myFootprint)/allDrive, places=4)
        # air_short disappears as long motorized, so only bus_short is left
        sb375Goal = 40.142892/7
        self.assertAlmostEqual(components[3], (sb375Goal - myFootprint)/sb375Goal, places = 4)

if __name__ == '__main__':
    unittest.main()
