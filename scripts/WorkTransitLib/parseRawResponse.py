import pandas as pd 
import sqlite3 
import numpy as np 
import datetime
import sys 
import os 
from ast import literal_eval
import logging 

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')


def parse_time(x):
    return(str(datetime.datetime.utcfromtimestamp(x)))

def parse_duration(x):
    return(np.round(x/3600.0, 2))

def parse_distance(x):
    return(np.round(x/1609.34, 2))

def remove_html_tags(text):
    """Remove html tags from a string"""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def summarize_leg_step(step):
    out = {}
    out['distance_mi'] = parse_distance(step['distance']['value'])
    out['duration_hr'] = parse_duration(step['duration']['value'])
    out['instructions'] = remove_html_tags(step['html_instructions'])

    out['distance_text'] = step['distance']['text']
    out['duration_text'] = step['duration']['text']

    out_series = pd.Series(out)
    return(out_series)


def consolidate_steps(driving_steps_dict):
    concise_steps = pd.DataFrame([summarize_leg_step(x) for x in driving_steps_dict])
    concise_steps = concise_steps.reset_index().rename({'index':'Step #'}, axis=1)
    concise_steps = concise_steps.sort_values('duration_hr', ascending=False)
    return(concise_steps)

def parse_driving_details(driving_resp):

    legs = driving_resp['legs'][0]
    concise_steps = consolidate_steps(legs['steps'])

    driving_details = {}
    driving_details['summary'] = driving_resp['summary']
    driving_details['duration_hr'] = parse_duration(legs['duration']['value'])
    driving_details['duration_text'] = legs['duration']['text']

    driving_details['duration_in_traffic_hr'] = parse_duration(legs['duration_in_traffic']['value'])
    driving_details['duration_in_traffic_text'] = legs['duration_in_traffic']['text']

    driving_details['extra time in traffic_min'] = np.round((driving_details['duration_in_traffic_hr'] - driving_details['duration_hr'])*60.0, 2)

    driving_details['distance_mi'] = parse_distance(legs['distance']['value'])


    driving_details['1st Longest Step (time)'] = str(concise_steps.iloc[0].to_dict())
    driving_details['2nd Longest Step (time)'] = str(concise_steps.iloc[1].to_dict())
    driving_details['3rd Longest Step (time)'] = str(concise_steps.iloc[2].to_dict())

    return(pd.Series(driving_details))


def parse_transit_details(transit_resp):
    transit_details = {}
    legs = transit_resp['legs'][0]
    transit_steps = [x for x in legs['steps'] if x['travel_mode'] == 'TRANSIT']
    lines = [x['transit_details']['line']['short_name'] for x in transit_steps]
    transit_details['departure_time'] = parse_time(legs['departure_time']['value'])
    transit_details['arrival_time'] = parse_time(legs['arrival_time']['value'])
    transit_details['duration_hr'] = parse_duration(legs['duration']['value'])
    transit_details['duration_txt'] = legs['duration']['text']
    transit_details['distance_mi'] = parse_distance(legs['distance']['value'])
    transit_details['transit lines'] = lines
    transit_details['transit departure_time'] = [parse_time(x['transit_details']['departure_time']['value']) 
                                         for x in transit_steps]
    transit_details['transit arrival_time'] = [parse_time(x['transit_details']['arrival_time']['value']) 
                                         for x in transit_steps]
    transit_details['transit durations_hr'] = [parse_duration(x.get('duration').get('value')) 
                                            for x in transit_steps]
    transit_details = {k:str(v) if type(v) == list else v 
                      for k, v in transit_details.items()}
    return(pd.Series(transit_details))


class RunParser():
    
    def __init__(self, mode, parsed_tbl_name):
        self.mode = mode
        if mode not in ['driving', 'transit']:
            raise ValueError()
        
        self.parsed_tbl_name = parsed_tbl_name
        if parsed_tbl_name not in ['parsed_transit', 'parsed_driving']:
            raise ValueError()
        
        if self.mode == 'transit':
            self.col_name = 'departure_time_y'
        elif self.mode == 'driving':
            self.col_name = 'departure_time'
        else:
            logger.warn("Mode not in [transit, driving] .. not sure departure time colname ")
                
    def create_con(self, db_path):
        self.con = sqlite3.connect(db_path)
        self.cursor = self.con.cursor()
        self.cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\' ORDER BY name')
        tables = self.cursor.fetchall()
        tables = [x[0] for x in tables]
        logger.debug("Tables: ", tables)
    
    def get_latest_date(self):
        sql = f"select max(date) as date, max(time) as time from {self.parsed_tbl_name}"
        date, time = self.cursor.execute(sql).fetchall()[0]
        logger.debug(f"Latest date for {self.parsed_tbl_name} is {date} {time}")
        return(date, time)
    
    def get_raw_responses_df(self, latest_date, latest_time):
        raw_df = pd.read_sql(f"""
            select * from raw_responses 
            where Date >= '{latest_date}'
            and Time >= '{latest_time}'
            and mode = '{self.mode}'
            """, self.con)
        logger.debug("Raw Response df has ", raw_df.shape[0], " rows")
        return(raw_df)
    
    def get_latest_date2(self):
        sql = f"select max({self.col_name}) as latest_date_time from {self.parsed_tbl_name}"
        latest_date_time = self.cursor.execute(sql).fetchall()[0][0]
        logger.debug(f"Latest date for {self.parsed_tbl_name} is {latest_date_time}")
        return(latest_date_time)
    
    def get_raw_responses_df2(self, latest_date_time):
        raw_df = pd.read_sql(f"""
            select * from raw_responses 
            where departure_time >= '{latest_date_time}'
            and mode = '{self.mode}'
            """, self.con)
        logger.debug("Raw Response df has ", raw_df.shape[0], " rows")
        return(raw_df)
    
    def parse_raw_df(self, raw_df):
        logger.debug("Starting parse raw")
        if self.mode =='transit':
            raw_df = raw_df[raw_df['Raw Response'] != '[]']
            transit_df_parsed = raw_df['Raw Response']\
                .apply(lambda x: parse_transit_details(literal_eval(x)[0]))
            return(transit_df_parsed)
        elif self.mode == 'driving':
            driving_df_parsed = raw_df['Raw Response']\
                .apply(lambda x: parse_driving_details(literal_eval(x)[0]))
            return(driving_df_parsed)
        else:
            logger.info("mode not transit or driving.... Unexpected returning empty df")
            return(pd.DataFrame())

    def merge(self, raw_df, parsed_df):
        full = pd.merge(parsed_df, raw_df
             , left_index=True, right_index=True)
        return(full)
    
    def update_table(self, full_df):
        full_df.to_sql(self.parsed_tbl_name, self.con, index=False, if_exists='append')
        self.con.commit()
        logger.debug(self.parsed_tbl_name, " was updated with ", full_df.shape[0], " rows")

    def execute(self
               , db_path = '/home/malcolm/WorkTransit/data/transit.db'
               , parsed_table_name = 'parsed_transit', column_name='date'):
        self.create_con(db_path)
#         self.latest_date, self.latest_time = self.get_latest_date()
#         self.raw_df = self.get_raw_responses_df(self.latest_date, self.latest_time)
        # Testing
        self.latest_date_time = self.get_latest_date2()
        self.raw_df = self.get_raw_responses_df2(self.latest_date_time)
        self.parsed_df = self.parse_raw_df(self.raw_df)
        self.full_df = self.merge(self.raw_df, self.parsed_df)
        self.update_table(self.full_df)









