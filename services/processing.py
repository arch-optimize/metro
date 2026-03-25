import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import os

from utils.constants import ALL_STATIONS, DISC_PROFILES
from services.scheduling import split_table_by_line

def get_0_1_idx_from_date(dt):
	h_idx=int(dt.split(" ")[1].split(":")[0])-4
	if h_idx<0:
		h_idx+=24
	m_idx=int(dt.split(" ")[1].split(":")[1])
	return h_idx,m_idx//2


def parse_uploaded_csv(df: pd.DataFrame) -> pd.DataFrame:
	df = df.copy()

	required_cols = [
		"Ημερομηνία χρήσης",
		"Αριθμός Κάρτας",
		"Προφίλ έκπτωσης",
		"Γραμμή",
		"Σταθμός",
		"Επιβίβαση",
	]
	missing_cols = [col for col in required_cols if col not in df.columns]
	if missing_cols:
		raise ValueError(f"Missing required columns: {missing_cols}")

	df["dtm"] = pd.to_datetime(
		df["Ημερομηνία χρήσης"],
		format="%d-%m-%Y %H:%M:%S",
		errors="coerce",
		cache=True,
	)
	df = df.dropna(subset=["dtm"]).copy()

	df["service_date"] = (df["dtm"] - pd.Timedelta(hours=4)).dt.date
	df["service_date_str"] = df["service_date"].astype(str)
	df["weekday_name"] = pd.to_datetime(df["service_date"]).dt.day_name()

	#df = df.sort_values(["Αριθμός Κάρτας", "dtm"]).reset_index(drop=True)
	return df


def build_output_filenames(processing_date, output_dir="stasy_data_processed"):
	output_path = Path(output_dir)
	output_path.mkdir(parents=True, exist_ok=True)

	date_str = processing_date.strftime("%d_%m_%Y")
	npy_path = output_path / f"origins_dests_{date_str}.npy"
	npz_path = output_path / f"info_{date_str}.npz"
	return npy_path, npz_path


def process_days(start_date, fin_date, load_path, save_path):
	curr_date=datetime.strptime(start_date, "%d/%m/%Y")
	end_date=datetime.strptime(fin_date, "%d/%m/%Y")
	skip_date=0
	df_next=[]
	drop_idx=[]
	while(curr_date<=end_date):
		if skip_date==1:
			skip_date=0
			curr_date+=timedelta(days=1)
			if curr_date>end_date:
				break
		rec_tracker=0
		print("getting data for "+str(curr_date.strftime("%d_%m_%Y")))
		today_invalid_date=0
		today_invalid_boarding_code=0
		today_invalid_id=0
		today_invalid_disc=0
		today_invalid_station=0
		today_data=np.zeros([24,30,70,70],dtype=np.int32) # hour index, 2-minute index,start station index, destination station index
		today_unmatched_entries=np.zeros([24,30,70],dtype=np.int32)
		today_unmatched_exits=np.zeros([24,30,70],dtype=np.int32)
		today_same_station_tracks=np.zeros([70],dtype=np.int32)
		today_duplicates=np.zeros([70],dtype=np.int32)
		today_almost_duplicates=np.zeros([70],dtype=np.int32)
		today_category_entries=np.zeros([24,30,70,len(DISC_PROFILES)],dtype=np.int32)
		today_category_exits=np.zeros([24,30,70,len(DISC_PROFILES)],dtype=np.int32)
		try:
			df.drop(drop_idx,inplace=True)
		except:
			pass
		if len(df_next) == 0:
			try:
				df=pd.read_csv(load_path+"/svdt_"+str(curr_date.strftime("%d_%m_%Y"))+".csv")
			except:
				skip_date=1
				continue
		drop_idx=[]
		next_date=curr_date+timedelta(days=1)
		try:
			df_next=pd.read_csv(load_path+"/svdt_"+str(next_date.strftime("%d_%m_%Y"))+".csv")
		except:
			df_next=[]
			skip_date=1
			continue
		df=pd.concat([df,df_next],ignore_index=True)
		df["dtm"]=pd.to_datetime(df["Ημερομηνία χρήσης"],format="%d-%m-%Y %H:%M:%S",cache=True)
		df=df.sort_values(["Αριθμός Κάρτας","dtm"])
		last_start=-1
		last_start_h_idx=-1
		last_start_m_idx=-1
		last_st_idx=-1
		last_h_idx=-1
		last_m_idx=-1
		pending_track=0
		pending_track_id='0'
		previous=()
		for row in df.itertuples(index=True):
			r=row[1:]
			if r[-1]<curr_date+timedelta(hours=4):
				continue
			if r[0] is None or (isinstance(r[0], float) and math.isnan(r[0])):
				today_invalid_date+=1
				continue
			if r[1] is None or (isinstance(r[1], float) and math.isnan(r[1])):
				today_invalid_id+=1
				continue
			if r[2] is None or (isinstance(r[2], float) and math.isnan(r[2])):
				today_invalid_disc+=1
			if r[4] is None or (isinstance(r[4], float) and math.isnan(r[4])):
				today_invalid_station+=1
				continue
			h_idx,m_idx=get_0_1_idx_from_date(r[0])
			st_idx=ALL_STATIONS.index(r[4])
			print("+++++++++++++++++++++++++++++++++++++++++++++++++++")
			print(r)
			if r[5]=='[B] Επιβίβαση':
				if r[-1]>next_date+timedelta(hours=4):
					if pending_track==1:
						print("recording unmatched entry at"+ALL_STATIONS[last_st_idx])
						today_unmatched_entries[last_h_idx,last_m_idx,last_st_idx]+=1
						pending_track=0
					continue
				if r==previous:
					print("ignoring duplicate record at "+ALL_STATIONS[st_idx])
					today_duplicates[st_idx]+=1
					continue
				if len(previous)==7 and r[1]==previous[1] and r[4]==previous[4] and r[5]==previous[5] and h_idx==last_h_idx and abs(m_idx-last_m_idx)<=5:
					print("ignoring almost duplicate record at "+ALL_STATIONS[st_idx])
					today_almost_duplicates[st_idx]+=1
					last_m_idx=m_idx
					previous=r
					continue
				if(r[2] in DISC_PROFILES):
					today_category_entries[h_idx,m_idx,st_idx,DISC_PROFILES.index(r[2])]+=1
				if pending_track==1:
					print("recording unmatched entry at"+ALL_STATIONS[last_st_idx])
					today_unmatched_entries[last_h_idx,last_m_idx,last_st_idx]+=1
				previous=r
				pending_track=1
				last_start=st_idx
				last_st_idx=st_idx
				last_h_idx=h_idx
				last_m_idx=m_idx
				last_start_h_idx=h_idx
				last_start_m_idx=m_idx
				pending_track_id=r[1]
			elif r[5]=='[D] Αποβίβαση':
				if r[-1]>next_date+timedelta(hours=4):
					if pending_track==0:
						continue
					elif pending_track_id!=r[1]:
						print("recording unmatched entry at"+ALL_STATIONS[last_st_idx])
						today_unmatched_entries[last_h_idx,last_m_idx,last_st_idx]+=1
						pending_track=0
						continue
				if r==previous:
					print("ignoring duplicate record at "+ALL_STATIONS[st_idx])
					today_duplicates[st_idx]+=1
					continue
				if len(previous)==7 and r[1]==previous[1] and r[4]==previous[4] and r[5]==previous[5] and h_idx==last_h_idx and abs(m_idx-last_m_idx)<=5:
					print("ignoring almost duplicate record at "+ALL_STATIONS[st_idx])
					today_almost_duplicates[st_idx]+=1
					last_m_idx=m_idx
					previous=r
					continue
				if(r[2] in DISC_PROFILES):
					today_category_exits[h_idx,m_idx,st_idx,DISC_PROFILES.index(r[2])]+=1
				u_flag=0
				if pending_track==0:
					print("recording unmatched exit at"+ALL_STATIONS[st_idx])
					today_unmatched_exits[h_idx,m_idx,st_idx]+=1
					u_flag=1
				if pending_track==1 and r[1]!=pending_track_id:
					print("recording unmatched exit at"+ALL_STATIONS[st_idx])
					today_unmatched_exits[h_idx,m_idx,st_idx]+=1
					print("recording unmatched entry at"+ALL_STATIONS[last_st_idx])
					today_unmatched_entries[last_h_idx,last_m_idx,last_st_idx]+=1
					u_flag=1
				last_st_idx=st_idx
				last_h_idx=h_idx
				last_m_idx=m_idx
				previous=r
				pending_track=0
				if u_flag==0:
					if last_start==st_idx:
						print("Ignoring same station track at "+ALL_STATIONS[st_idx])
						today_same_station_tracks[st_idx]+=1
						continue
					rec_tracker+=1
					print("Recording track from "+ALL_STATIONS[last_start]+" to "+ALL_STATIONS[st_idx]+" at "+str((last_start_h_idx+4)%24)+":"+str(last_start_m_idx*2))
					today_data[last_start_h_idx,last_start_m_idx,last_start,st_idx]+=1
			else:
				today_invalid_boarding_code+=1
		if pending_track==1: #check for unmatched final entry
			print("recording unmatched entry at"+ALL_STATIONS[last_st_idx])
			today_unmatched_entries[last_h_idx,last_m_idx,last_st_idx]+=1
		filename1=save_path+"/origins_dests_"+str(curr_date.strftime("%d_%m_%Y"))+".npy"
		np.save(filename1,today_data)
		filename2=save_path+"/info_"+str(curr_date.strftime("%d_%m_%Y"))+".npz"
		np.savez(
		filename2,
		today_invalid_date=today_invalid_date,
			today_invalid_boarding_code=today_invalid_boarding_code,
			today_invalid_id=today_invalid_id,
			today_invalid_disc=today_invalid_disc,
			today_invalid_station=today_invalid_station,
			today_unmatched_entries=today_unmatched_entries,
			today_unmatched_exits=today_unmatched_exits,
			today_category_entries=today_category_entries,
			today_category_exits=today_category_exits,
			today_same_station_tracks=today_same_station_tracks,
			today_duplicates=today_duplicates,
			today_almost_duplicates=today_almost_duplicates
		)
	#	print("Total unmatched entries:",today_unmatched_entries.sum())
	#	print("Total unmatched exits:",today_unmatched_exits.sum())
	#	print("Total duplicates:",today_duplicates.sum())
	#	print("Total almost duplicates:",today_almost_duplicates.sum())
	#	print("Total same station tracks:",today_same_station_tracks.sum())
	#	print("Total recorded tracks:",rec_tracker)
		curr_date+=timedelta(days=1)


def save_processed_outputs(today_data, info_dict, processing_date, output_dir="stasy_data_processed"):
	npy_path, npz_path = build_output_filenames(processing_date, output_dir=output_dir)

	np.save(npy_path, today_data)
	np.savez(
		npz_path,
		today_invalid_date=info_dict["today_invalid_date"],
		today_invalid_boarding_code=info_dict["today_invalid_boarding_code"],
		today_invalid_id=info_dict["today_invalid_id"],
		today_invalid_disc=info_dict["today_invalid_disc"],
		today_invalid_station=info_dict["today_invalid_station"],
		today_unmatched_entries=info_dict["today_unmatched_entries"],
		today_unmatched_exits=info_dict["today_unmatched_exits"],
		today_category_entries=info_dict["today_category_entries"],
		today_category_exits=info_dict["today_category_exits"],
		today_same_station_tracks=info_dict["today_same_station_tracks"],
		today_duplicates=info_dict["today_duplicates"],
		today_almost_duplicates=info_dict["today_almost_duplicates"],
	)

	return str(npy_path), str(npz_path)

def processed_to_training(path):
	if path.strip()[-1]!="/":
		path=path.strip()+"/"
	l=os.listdir(path)
	rows=[]
	for name in l:
		if name[-4:]==".npy" and name[:13]=="origins_dests":
			print(name)
			day=int(name.split("_")[2])
			month=int(name.split("_")[3])
			year=int(name.split("_")[4].split(".")[0])
			data=np.load(path+name)
			data=data.sum(axis=1)
			l1,l2,l3=split_table_by_line(data)
			for i in range(24):
				demand_1=int(l1[i].sum())
				demand_2=int(l2[i].sum())
				demand_3=int(l3[i].sum())
				rows.append([year,month,day,i,demand_1,demand_2,demand_3])
	df=pd.DataFrame(rows, columns=["year","month","day","hour","demand1", "demand2", "demand3"])
	return df

def process_ats(path):
	if path.strip()[-1]!="/":
		path=path.strip()+"/"
	col_names=[ "EventID", "timestamp", "localeID", "roleID", "tripId", "serviceId", "arrivalTime", "departureTime", "plannedArrivalTime", "plannedDepartureTime", "arrivalDelay", "departureDelay", "dateRecord", "direction", "lineOperatingMode", "event", "dwellTime", "line", "runningTime", "precedentStationId", "platformId", "stationId", "tableReferenceId", "trainId", "geographical", "headway", "CrewID", "SpeedProfile", "Coasting", "PropertyBagTrain"]
	names=os.listdir(path)
	df=pd.DataFrame()
	for name in names:
		if name[:4]=="ATS_":
			tmp=pd.read_csv(path+name,header=None,names=col_names)[["dwellTime","runningTime","precedentStationId","stationId"]]
			df=pd.concat([df,tmp])
	df["total_time"]=df["dwellTime"]+df["runningTime"]
	df_group=df.groupby(['precedentStationId', 'stationId'])['total_time'].mean().reset_index()
	return df_group

def process_uploaded_dataframe(s_date, f_date, l_path, s_path):
	process_days(s_date, f_date, l_path, s_path)
