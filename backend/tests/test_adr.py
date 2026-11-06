import unittest
import pandas as pd
from adr import calculate_adr


class ADRTests(unittest.TestCase):
    def calculate(self, events, positions=None, ends=None, health=None):
        columns = ['tick','attacker_steamid','user_steamid','attacker_team_num','user_team_num','dmg_health','health','weapon']
        return calculate_adr(pd.DataFrame(events, columns=columns),
            [{'round':1,'live_start_tick':10,'end_tick':30}, {'round':2,'live_start_tick':30,'end_tick':60}],
            pd.DataFrame(ends if ends is not None else [(25,'CT'),(55,'T')], columns=['tick','winner']),
            pd.DataFrame(positions if positions is not None else [(10,'1',2),(30,'1',3)], columns=['tick','steamid','team_num']),
            pd.DataFrame(health if health is not None else [(19,'2',30)], columns=['tick','steamid','health']), '1')

    def test_caps_overkill_and_counts_zero_damage_round(self):
        result=self.calculate([(20,'1','2',2,3,110,0,'awp')])
        self.assertEqual((result['value'],result['known_damage'],result['rounds_played']),(15,30,2))

    def test_excludes_self_team_world_c4_warmup_and_post_round(self):
        events=[(20,'1','1',2,2,20,80,'hegrenade'),(20,'1','2',2,2,20,10,'ak47'),
                (20,'1','2',2,3,20,0,'world'),(20,'1','2',2,3,20,0,'planted_c4'),
                (9,'1','2',2,3,20,10,'ak47'),(26,'1','2',2,3,20,0,'ak47')]
        self.assertEqual(self.calculate(events)['value'],0)

    def test_utility_damage_after_attacker_death_and_halftime_sides(self):
        events=[(20,'1','2',2,3,20,10,'inferno'),(40,'1','2',3,2,10,20,'hegrenade')]
        result=self.calculate(events,health=[(19,'2',30),(39,'2',30)])
        self.assertEqual(result['value'],15)

    def test_same_tick_hits_use_remaining_health_in_order(self):
        events=[(20,'3','2',2,3,20,10,'ak47'),(20,'1','2',2,3,90,0,'awp')]
        self.assertEqual(self.calculate(events)['known_damage'],10)

    def test_joined_late_does_not_count_round_before_participation(self):
        result=self.calculate([],positions=[(35,'1',3)])
        self.assertEqual(result['rounds_played'],1)
        self.assertEqual(result['value'],0)

    def test_missing_prehealth_does_not_invent_damage(self):
        result=self.calculate([(20,'1','2',2,3,110,0,'awp')],health=[])
        self.assertIsNone(result['value']); self.assertEqual(result['status'],'partial')

    def test_unknown_side_or_damage_is_partial(self):
        for event in [(20,'1','2',None,3,20,10,'ak47'),(20,'1','2',2,3,None,10,'ak47')]:
            self.assertIsNone(self.calculate([event])['value'])

    def test_incomplete_round_is_not_silently_counted(self):
        result=self.calculate([],ends=[(25,'CT')])
        self.assertEqual(result['rounds_played'],1);self.assertIsNone(result['value'])

    def test_missing_stream_or_columns_is_unavailable(self):
        self.assertEqual(calculate_adr(None,[],None,None,None,'1')['status'],'unavailable')
        self.assertEqual(calculate_adr(pd.DataFrame(),[],pd.DataFrame(),pd.DataFrame(),None,'1')['status'],'unavailable')

    def test_no_participation_cannot_be_zero_adr(self):
        self.assertIsNone(self.calculate([],positions=[])['value'])

    def test_corrupt_tick_or_float_steamid_does_not_fabricate_zero(self):
        self.assertIsNone(self.calculate([(None,'1','2',2,3,20,10,'ak47')])['value'])
        self.assertIsNone(self.calculate([(20,76561199636557537.0,'2',2,3,20,10,'ak47')])['value'])
        self.assertIsNone(self.calculate([(20,'1','2',2,3,20,10,'ak47')],health=[(None,'2',30)])['value'])
