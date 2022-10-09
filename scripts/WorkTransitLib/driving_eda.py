import sqlite3 
import pandas as pd 
import numpy as np 
import datetime 
import sys
import os 

import plotly.express as px
from plotly.subplots import make_subplots
import plotly.subplots as sp
import plotly.graph_objects as go

sys.path.append('/home/malcolm/WorkTransit/scripts/')
from WorkTransitLib import RawDirections as rd
rev_locations = {v:k for k, v in rd.locations.items()}


def gb_summary_func(df):
    out = {}
    out['Count'] = df.shape[0]
    out['Avg Duration Traffic hr'] = np.round(df['duration_in_traffic_hr'].mean(), 2)
    out['Stdev Duration Traffic hr'] = np.round(df['duration_in_traffic_hr'].std(), 2)
    out['Avg Duration Traffic text'] = str(np.round(out['Avg Duration Traffic hr'] * 60, 2) ) + ' mins'
    out['Stdev Duration Traffic text'] = str(np.round(out['Stdev Duration Traffic hr'] * 60, 2) ) + ' mins'
    out['Avg Duration Mins num'] = np.round(out['Avg Duration Traffic hr'] * 60, 2)
    out['Stdev Duration Min num'] = np.round(out['Stdev Duration Traffic hr'] * 60, 2)
    out['Avg Duration Traffic Mins num'] = np.round(out['Avg Duration Traffic hr'] * 60, 2)
    out['Earliest Time'] = df['Time'].min()
    out['Latest Time'] = df['Time'].max()
    out['Earliest Date'] = df['Date'].min()
    out['Latest Date'] = df['Date'].max()
    out['Days w/ Data'] = df['Date'].nunique()

    out_series = pd.Series(out)
    return(out_series)
    
def create_leave_time_gb(df, with_col='Day of Week'):
    time_gb = df.set_index('departure_time_time')\
        .groupby([with_col, pd.Grouper(freq='20T')])\
        .apply(lambda x: gb_summary_func(x))
    time_gb2 = time_gb.reset_index()
    time_gb2 = time_gb2
    print(time_gb2)
    time_gb2['Earliest Start Time'] = pd.to_datetime(time_gb2['Earliest Time'])
    return(time_gb2)


def create_avg_time_plot(gb_df, seg_field = 'Day of Week', routename = 'Unknown'):
    ## Deprecated for subplot class function 
    fig = px.line(gb_df, 'Earliest Start Time', 'Avg Duration Mins num'
           , color=seg_field, markers=True
           , title = f"Avg Time to dest by Leave Time by {seg_field} - " + routename)
    return(fig)
    
class SummarizeDriving():
    
    def __init__(self, **kwargs):
        self.db_path='/home/malcolm/WorkTransit/data/transit.db'
        self.end_dt = datetime.datetime.now()
        self.end_str = str(self.end_dt.date())
        n_days=14
        self.start_dt = self.end_dt - datetime.timedelta(days=n_days)
        self.start_str = str(self.start_dt.date())
        self.image_save_path = '/home/malcolm/WorkTransit/images/'
        os.makedirs(self.image_save_path, exist_ok=True)
        self.__dict__.update(**kwargs)        
        
        self.image_paths = []
        self.output_dfs = {}
    
    def create_con(self):
        self.con = sqlite3.connect(self.db_path)
        self.cursor =self. con.cursor()
        self.cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\' ORDER BY name')
        tables = self.cursor.fetchall()
        tables = [x[0] for x in tables]
        print("Tables: ", tables)
    
    def load_data(self):
        # Load Data with Modifications
        df = pd.read_sql(f""" 
        select * 
        from parsed_driving
        where Date between '{self.start_str}' and '{self.end_str}'
        order by Date
        """, self.con)
        print(df.shape)
        df['departure_time'] = pd.to_datetime(df['departure_time'])
        df['departure_time_time'] = df['departure_time'].apply(lambda x: x - pd.Timestamp(x.date()))
        df['origin_name'] = df['origin'].apply(lambda x: rev_locations.get(x, 'Unknown'))
        df['destination_name'] = df['destination'].apply(lambda x: rev_locations.get(x, 'Unknown'))
        df['Day of Week'] = df['departure_time'].dt.dayofweek.astype(str) + '-' + df['departure_time'].dt.day_name()
        df = df.rename({'summary':'route'}, axis=1)
        self.df = df.copy()
        
    def create_one_route_subplots(self, route_plot, time_plot, routename):

        figure1_traces = []
        figure2_traces = []
        for trace in range(len(time_plot["data"])):
            temp_trace = time_plot["data"][trace]
            temp_trace['legendgroup'] = 'Day of Week'
        #     temp_trace['showlegend'] = False
            figure1_traces.append(temp_trace)
        for trace in range(len(route_plot["data"])):
            temp_trace = route_plot["data"][trace]
            temp_trace['legendgroup'] = 'Route'
            figure2_traces.append(temp_trace)

        #Create a 1x2 subplot
        this_figure = sp.make_subplots(rows=2, cols=1 
                   , subplot_titles=(f"Avg Time bw {routename} by Day of Week and Time of Day"
                                     , f"Avg Time bw {routename} by Route and Time of Day"))
        # Get the Express fig broken down as traces and add the traces to the proper plot within in the subplot
        for traces in figure1_traces:
            this_figure.append_trace(traces, row=1, col=1)
        for traces in figure2_traces:
            this_figure.append_trace(traces, row=2, col=1)

        fig1 = go.Figure(this_figure)
        fig1.update_layout(
            height=800, 
            width=800, 
            title_text= f"Day of Week and Route Avg Drive time for {routename}",

            xaxis2_title = 'Time (of Day)',
            yaxis2_title = 'Mins to Work',
            xaxis1_title = 'Time (of Day)',
            yaxis1_title = 'Mins to Work',
            legend_tracegroupgap = 290,

        )
        return(fig1)
    
    def one_route_pipeline(self, origin_name, dest_name):
        routename = origin_name + ' - ' + dest_name
        route1 = self.df[(self.df['origin_name'] == origin_name) 
                & (self.df['destination_name'] == dest_name)  
    #             & (df['Date'] == day1)
               ]
        time_gb = create_leave_time_gb(route1, 'Day of Week')
        route_gb = create_leave_time_gb(route1, 'route')
        
        time_plot = create_avg_time_plot(time_gb, 'Day of Week', routename)
        route_plot = create_avg_time_plot(route_gb, 'route', routename)
        subplots_plot = self.create_one_route_subplots(route_plot, time_plot, routename)
        
        subplot_plot_path = self.image_save_path + 'dayofweek_route_'+routename+'.png'
        subplots_plot.write_image(subplot_plot_path)
        
        self.image_paths.append(subplot_plot_path)
        print("Saved Image for ", routename)
        
        df_summ = gb_summary_func(route1)
        df_summ = pd.DataFrame(df_summ).T\
            .drop(['Avg Duration Traffic hr', 'Stdev Duration Traffic hr', 
                  'Avg Duration Mins num', 'Stdev Duration Min num', 'Avg Duration Traffic Mins num'], axis=1)
        df_summ = df_summ.rename({0:routename})
        return(df_summ)

        
    def run_multiple_trips(self):
        self.summ_dicts = []
        pairs = [
            {'origin_name' : 'home',   'dest_name': 'work'},
            {'origin_name' : 'work',   'dest_name': 'home'},
            {'origin_name' : 'bxbark', 'dest_name': 'work'},
            {'origin_name' : 'work',   'dest_name': 'bxbark'},
        ]
        for pair in pairs:
            print("Working on ", pair)
            rslt = self.one_route_pipeline(**pair)
            self.summ_dicts.append(rslt)
            
        self.trip_summary_df = pd.concat(self.summ_dicts)
        self.output_dfs['Trip Summary'] = self.trip_summary_df
            
    
    def execute(self):
        self.create_con()
        self.load_data()
        self.run_multiple_trips()
        
        
if __name__ == '__main__':
    driving_sum = SummarizeDriving()
    driving_sum.execute()
    driving_sum.trip_summary_df
    print("Images located at: ", driving_sum.image_paths)