#!/usr/bin/python
import psycopg2
import datetime
from bcreg.config import config
from bcreg.eventprocessor import EventProcessor, CORP_TYPES_IN_SCOPE
from bcreg.bcregistries import BCRegistries, system_type, AMALGAMATION_TYPES_SCOPE


specific_corps = [
                    '0641655',
                    '0820416',
                    '0700450',
                    '0803224',
                    'LLC0000192',
                    'C0277609',
                    'A0072972',
                    'A0051862',
                    'C0874156',
                    '0874244',
                    '0593707',
                    'A0068919',
                    'A0064760',
                    'LLC0000234',
                    'A0077118',
                    'A0062459',
                    '0708325',
                    '0679026',
                    '0707774',
                    'C0874057',
                    'A0028374',
                    'A0053381',
                    'A0051632',
                    '0578221',
                    'A0032100',
                    '0874088',
                    '0803207',
                    '0873646',
                    '0078162',
                    '0754041',
                    'XS1000180',
                    'LP1000140',
                    'A0059911',
                    'S1000080',
                    '0637981',
                    'A0051632',
                    '0578221',
                    '0497648',
                    'A0038634',
                    '0136093',
                    '0869404',
                    '0641396',
                    'LP0745132',
                    'C0283576',
                    '0860306',
                    '0673578',
                    '0763302',
                    '0860695',
                    'A0039853',
                    'A0036994',
                    '1185488',
                    '0979020',
                    '0354136',
                    '1164165',
                    '1059630',
                    '0093733',
                    '0197646',
                    'A0082127',
                    '0206786',
                    '0908182',
                    'FM005513',
                    '0616651',
                    'FM0418446',
                    'FM0464421',
                    'FM0464206',
                    '0143311',
                    '0006965',
                    'A0008669',
                    '0206483',
                    '0287583',
                    '0517093',
                    '0046062',
                    '0545062',
                    'A0027307',
                    '0046397',
                    '0503852',
                    'A0053913',
                    '0358554',
                    'C0184104',
                    'C0429174',
                    'A0020540',
                    '0693705',
                    '1101218',
                    '0650761',
                    '0928747',
                    '0347474',
                    '1101218',
                    '0450252',
                    'A0056744',
                    'A0087698',
                    'A0087699',
                    '0296354',
                    '0859276',
                    'A0045786',
                    '0791684',
                    '0675400',
                    '0675765',
                    'A0107449',
                    'A0107446',
                    'A0107438',
                    '1181944',
                    'A0107427',
                    'A0107426',
                    'A0107424',
                    'A0107423',
                    '0142362',
                    'FM0550949',
                    'FM0501860',
                    '0643505',
                    '0510537',
                    'C0733137',
                    'FM0327778',
                    'FM0327777',
                    'FM0327770',
                    'FM0327756',
                    '1188712',
                    '0855234',
                    'A0093289',
                    'A0053723',
                    'A0082657',
                    '0319629',
                    '0747962',
                    'A0011423',
                    'A0080841',
                    '0945957',
                    'A0092209',
                    'A0070194',
                    '0338518',
                    '1199242',
                    '0072808',
                    '0946908',
                    '0730909',
                    '1198849',
                    '0149514',
                    '0390058',
                    ]

with BCRegistries() as bc_registries:
    # get 5 corps for each type in scope (in addition to the above list)
    print('select corps for each type')
    for corp_type in CORP_TYPES_IN_SCOPE:
        print(corp_type)
        sql = """
                select corp_num
                from bc_registries.corporation
                where corp_typ_cd = '""" + corp_type + """'
                order by corp_num desc
                limit 15
               """
        corps = bc_registries.get_bcreg_sql("corps_by_type", sql, cache=False)
        n_corps = len(corps)
        for i in range(n_corps):
            specific_corps.append(corps[i]['corp_num'])

    # get 5 corps for each filing type in scope (in addition to the above list)
    print('select corps for each amalgamation filing')
    for filing_type in AMALGAMATION_TYPES_SCOPE:
        print(filing_type)
        sql1 = """
                select event_id
                from bc_registries.filing
                where filing_typ_cd = '""" + filing_type + """'
                order by effective_dt desc
                limit 5
               """
        sql2 = """
                select corp_num
                from bc_registries.event
                where event_id in (!EVENTS!)
               """
        sql3 = """
                select corp_num
                from bc_registries.corp_involved
                where event_id in (!EVENTS!)
               """
        events = bc_registries.get_bcreg_sql("events_by_filing", sql1, cache=False)
        n_events = len(events)
        if 0 < n_events:
            event_ids = ''
            for i in range(n_events):
                if i > 0:
                    event_ids = event_ids + ', '
                event_ids = event_ids + str(events[i]['event_id'])
            corp_sql = sql2.replace('!EVENTS!', event_ids)
            corps = bc_registries.get_bcreg_sql("corps_by_filing1", corp_sql, cache=False)
            n_corps = len(corps)
            for i in range(n_corps):
                specific_corps.append(corps[i]['corp_num'])
            corp_sql = sql3.replace('!EVENTS!', event_ids)
            corps = bc_registries.get_bcreg_sql("corps_by_filing2", corp_sql, cache=False)
            n_corps = len(corps)
            for i in range(n_corps):
                specific_corps.append(corps[i]['corp_num'])

    # ensure we have a unique list
    specific_corps = list({s_corp for s_corp in specific_corps})

    with EventProcessor() as event_processor:
        print("Get last processed event")
        prev_event_id = 0

        print("Get last max event")
        max_event_date = bc_registries.get_max_event_date()
        max_event_id = bc_registries.get_max_event(max_event_date)
        #max_event_id = 101944500 
        #max_event_date = bc_registries.get_event_id_date(max_event_id)
        
        # get specific test corps (there are about 6)
        print("Get specific corps")
        corps = bc_registries.get_specific_corps(specific_corps)
        
        print("Find unprocessed events for each corp")
        last_event_dt = bc_registries.get_event_effective_date(prev_event_id)
        max_event_dt = bc_registries.get_event_effective_date(max_event_id)
        corps = bc_registries.get_unprocessed_corp_events(prev_event_id, last_event_dt, max_event_id, max_event_dt, corps)
        
        print("Update our queue")
        event_processor.update_corp_event_queue(system_type, corps, max_event_id, max_event_date)
