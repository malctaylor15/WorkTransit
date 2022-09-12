#!/usr/bin/env python
# coding: utf-8

# In[7]:


import requests
import pickle
import json
import os
import sys
import googlemaps
import datetime 
import sqlite3
import pandas as pd
from ast import literal_eval

locations = dict(home = "120 Benchley Pl, Bronx NY",
work = "809 Washington Street",
bxbark = "830 Pelham Pkwy, Pelham Manor, NY 10803",
orchard_beach = "Orchard Beach, Bronx, NY 10464" ,
                )

home = "120 Benchley Pl, Bronx NY"
work = "809 Washington Street"
bxbark = "830 Pelham Pkwy, Pelham Manor, NY 10803"
orchard_beach = "Orchard Beach, Bronx, NY 10464"
now = datetime.datetime.now() + datetime.timedelta(minutes=3)

parameter_sets = dict(
    home_work_driving = {'origin' : home
                     , 'destination' : work
                     , 'mode' : "driving"
                     , 'departure_time' : now}, 
    home_work_transit = {'origin' : home
                     , 'destination' : work
                     , 'mode' : "transit"
                     , 'departure_time' : now}, 
    work_home_transit = {'origin' : work
                     , 'destination' : home
                     , 'mode' : "transit"
                     , 'departure_time' : now}, 
    work_home_driving = {'origin' : work
                     , 'destination' : home
                     , 'mode' : "driving"
                     , 'departure_time' : now}, 
    home_bxbark_driving = {'origin' : home
                     , 'destination' : bxbark
                     , 'mode' : "driving"
                     , 'departure_time' : now}, 
    bxbark_work_driving = {'origin' : bxbark
                     , 'destination' : work
                     , 'mode' : "driving"
                     , 'departure_time' : now}, 
    work_bxbark_driving = {'origin' : work
                     , 'destination' : bxbark
                     , 'mode' : "driving"
                     , 'departure_time' : now}, 
    bxbark_home_driving = {'origin' : work
                     , 'destination' : bxbark
                     , 'mode' : "driving"
                     , 'departure_time' : now}, 
    home_beach_driving = {'origin' : home
                     , 'destination' : orchard_beach
                     , 'mode' : "driving"
                     , 'departure_time' : now}, 
    beach_home_driving = {'origin' : orchard_beach
                     , 'destination' : home
                     , 'mode' : "driving"
                     , 'departure_time' : now}, 
) 



class GetRawAPI():
    
    def __init__(self, start_time):
        print("Let's get started")
        self.start_time = start_time
        pass

    def create_param_sets(self, param_names):
        param_set_list = [parameter_sets[x] for x in param_names]
        for param_set in param_set_list:
            param_set['departure_time'] = self.start_time
        return(param_set_list)

    @staticmethod
    def get_gmap_directions(param_set_list, google_key_path):
        # Start google client 
        with open(google_key_path, 'rb') as hnd:
            api_key = pickle.load(hnd)
        gmaps = googlemaps.Client(key=api_key)

        # Make API Calls 
        updated_params_list = []
        for param_set in param_set_list:
            param_set2 = param_set.copy()
            temp_result = gmaps.directions(**param_set)

            date = str(param_set2['departure_time'].date())
            time = str(param_set2['departure_time'].strftime('%H:%M'))
            param_set2.update({'Raw Response' : temp_result
                              , 'Date' : date
                              , 'Time' : time})
            updated_params_list.append(param_set2)

        # Fix up dataframe 
        updated_params_df = pd.DataFrame(updated_params_list)
        updated_params_df['Raw Response'] = updated_params_df['Raw Response'].astype(str)
        updated_params_df['departure_time'] = updated_params_df['departure_time'].astype(str)
        return(updated_params_df)

    @staticmethod
    def update_db(updated_params_df, db_path, db_file_name):
        # Ensure paths and files are ready 
        os.makedirs(db_path, exist_ok=True)
        if db_path[-1] != '/':
            db_path = db_path + '/'
        db_loc = db_path + db_file_name
        
        # Create SQL Connection and append to db
        con = sqlite3.connect(db_loc)
        updated_params_df.to_sql('Raw_Responses', con, index=False, if_exists='append' )
        
        # Close connection
        con.commit()
        con.close()
        print(f"Added to {db_loc}")
    
    def execute(self
                , param_names = ['home_work_driving', 'home_work_transit', 'home_bxbark_driving', 'bxbark_work_driving']
                , google_key_path = '/home/malcolm/credentials/google_transit_api.pkl'
                , db_path = '/home/malcolm/WorkTransit/data/'
                , db_file_name = 'transit.db'
               ):
        self.param_set_list = self.create_param_sets(param_names)
        self.updated_params_df = self.get_gmap_directions(self.param_set_list, google_key_path = google_key_path)
        self.update_db(self.updated_params_df, db_path = db_path, db_file_name = db_file_name)

        

# In[11]:
## Going to work params
# param_names = ['home_work_driving', 'home_work_transit', 'home_bxbark_driving', 'bxbark_work_driving']
## Coming from work params 
# param_names = ['work_home_driving', 'work_home_transit', 'work_bxbark_driving', 'bxbark_home_driving']

# db_updater = GetRawAPI()
# db_updater.execute()

# print(db_updater.updated_params_df)

