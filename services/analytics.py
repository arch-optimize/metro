import numpy as np
from datetime import date, datetime, timedelta
import os
from utils.constants import DISC_PROFILES

def orthodox_easter(year):
	a = year % 4
	b = year % 7
	c = year % 19
	d = (19*c + 15) % 30
	e = (2*a + 4*b - d + 34) % 7
	month = (d + e + 114) // 31
	day = ((d + e + 114) % 31) + 1
	julian_easter = date(year, month, day)
	return julian_easter + timedelta(days=13)

def get_special_days(year):
	easter = orthodox_easter(year)
	clean_monday = easter - timedelta(days=48)
	holy_week_start = easter - timedelta(days=7)
	holy_week = [(holy_week_start + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(7)]
	easter_week_start = easter + timedelta(days=1)
	easter_week = [(easter_week_start + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(7)]
	first_week = [(date(year, 1, i).strftime("%d/%m/%Y")) for i in range(1, 7)]
	last_week = [(date(year, 12, i).strftime("%d/%m/%Y")) for i in range(24, 32)]
	return (first_week, last_week,holy_week,easter_week,clean_monday.strftime("%d/%m/%Y"))

def smooth_month_outliers(month_data,month_masks):
#month_data: [[[24,30,70,70],...],[..],[..],[..],[..],[..],[..]]
	for i in range(7):
		base_mask=np.zeros([24,30,70,70])
		base_data=np.zeros([24,30,70,70])
		for j in range(len(month_data[i])):
			curr_dt=month_data[i][j]*month_masks[i][j]
			base_data+=curr_dt
			base_mask+=month_masks[i][j]
		month_weekday_avg=base_data/base_mask
		for j in range(len(month_data[i])):
			large_outlier_idx=month_data[i][j]>3*month_weekday_avg
			month_data[i][j][large_outlier_idx]=3*month_weekday_avg[large_outlier_idx]
			small_outlier_idx=month_data[i][j]<0.2*month_weekday_avg
			month_data[i][j][small_outlier_idx]=0.2*month_weekday_avg[small_outlier_idx]

def find_deviation_sum_selective(month_avg_data,month_avg_masks,dev_data,dev_day_idx, idx_from_to, event_duration):
#idx_from_to: [(fr1,to1),(fr2,to2),...]->data_of_interest=month_avg_data[i][idx_from_to[i][0]:idx_from_to[i][1]]
	base_mask=np.zeros([event_duration,30,70,70])
	base_dev=np.zeros([event_duration,30,70,70])
	for i in range(len(dev_day_idx)):
		base_dev+=dev_data[i]-month_avg_data[dev_day_idx[i]][idx_from_to[i][0]:idx_from_to[i][1]]
		base_mask+=month_avg_masks[dev_day_idx[i]][idx_from_to[i][0]:idx_from_to[i][1]]
	return base_dev,base_mask

def create_plot_arrays(
	curr_date,
	end_date,
	non_periodic_special_dates,
	special_hours,
	excluded_dates,
	load_folder,
	save_folder,
	hour_zero=4,
	special_event_duration=5,
	illegal_boarding_rate=0.1
):
	#periodic_special_days=["25/03","08/03",...]
	#curr_date=datetime.strptime("01/01/2024", "%d/%m/%Y")
	#end_date=datetime.strptime("1/11/2024", "%d/%m/%Y")
	init_year=int(curr_date.strftime("%Y"))
	fin_year=int(end_date.strftime("%Y"))
	cy=init_year
	fw=[]
	lw=[]
	mv=[]
	vp=[]
	kd=[]
	while cy<=fin_year:
		holidays=get_special_days(cy)
		fw.append(holidays[0])
		lw.append(holidays[1])
		mv.append(holidays[2])
		vp.append(holidays[3])
		kd.append(holidays[4])
		cy+=1
	#non_periodic_special_dates=["05/03/2023","08/03/2023","16/03/2023","08/02/2024","20/02/2024","22/02/2024","08/03/2024","07/02/2025","14/02/2025"]
	#special_hours=[11,12,11,11,12,12,8,12,11,12,11]
	#excluded_dates=["20/11/2024","28/02/2025","09/04/2025"]
	days=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
	curr_month=curr_date.strftime("%m")
	curr_month_data_per_weekday=[[],[],[],[],[],[],[]]
	curr_month_data_per_weekday_masks=[[],[],[],[],[],[],[]]
	curr_all_data_per_weekday=[[],[],[],[],[],[],[]]
	curr_all_data_per_weekday_masks=[[],[],[],[],[],[],[]]
	non_periodic_data=[]
	non_periodic_day_idx=[]
	non_periodic_from_to_idx=[]
	total_event_dev_sum=np.zeros([special_event_duration,30,70,70])
	total_event_dev_sum_mask=np.zeros([special_event_duration,30,70,70])
	fw_data=[[],[],[],[],[],[]]
	fw_data_masks=[[],[],[],[],[],[]]
	lw_data=[[],[],[],[],[],[],[],[]]
	lw_data_masks=[[],[],[],[],[],[],[],[]]
	mv_data=[[],[],[],[],[],[],[]]
	mv_data_masks=[[],[],[],[],[],[],[]]
	vp_data=[[],[],[],[],[],[],[]]
	vp_data_masks=[[],[],[],[],[],[],[]]
	kd_data=[]
	kd_data_masks=[]
	year=curr_date.strftime("%Y")
	while(1):
		month=curr_date.strftime("%m")
		br=0
		if(curr_date>end_date):
			br=1
		####
		if month!=curr_month or br==1:
			print("Processing month...")
			month_avg=[]
			month_avg_masks=[]
			#smooth_month_outliers(curr_month_data_per_weekday,curr_month_data_per_weekday_masks)
			for i in range(7):
				base_mask=np.zeros([24,30,70,70])
				base_data=np.zeros([24,30,70,70])
				month_weekday_min=np.ones([24,30,70,70])*np.inf
				month_weekday_max=-np.ones([24,30,70,70])*np.inf
				for j in range(len(curr_month_data_per_weekday[i])):
					curr_dt=curr_month_data_per_weekday[i][j]*curr_month_data_per_weekday_masks[i][j]
					#curr_month_data_per_weekday[np.isnan(curr_month_data_per_weekday)]=0
					month_weekday_min=np.minimum(month_weekday_min,curr_dt)
					month_weekday_max=np.maximum(month_weekday_max,curr_dt)
					base_data+=curr_dt
					base_mask+=curr_month_data_per_weekday_masks[i][j]
				month_weekday_avg=base_data/base_mask
				month_avg.append(month_weekday_avg)
				mm_tmp=np.ones(base_mask.shape)
				mm_tmp[base_mask==0]=0
				month_avg_masks.append(mm_tmp)
				flnm=save_folder+"/"+year+"/"+curr_month+"/"+days[i]+"/data_avg.npy"
				os.makedirs(os.path.dirname(flnm), exist_ok=True)
				np.save(flnm,month_weekday_avg)
				flnm=save_folder+"/"+year+"/"+curr_month+"/"+days[i]+"/data_min.npy"
				os.makedirs(os.path.dirname(flnm), exist_ok=True)
				np.save(flnm,month_weekday_min)
				flnm=save_folder+"/"+year+"/"+curr_month+"/"+days[i]+"/data_max.npy"
				os.makedirs(os.path.dirname(flnm), exist_ok=True)
				np.save(flnm,month_weekday_max)
			if len(non_periodic_day_idx)>0:
				p_tmp,m_tmp=find_deviation_sum_selective(month_avg,month_avg_masks,non_periodic_data,non_periodic_day_idx,non_periodic_from_to_idx,special_event_duration)
				total_event_dev_sum+=p_tmp
				total_event_dev_sum_mask+=m_tmp
				print("+++++++++++++++++++++++++++++++++++")
				print(np.sum(m_tmp))
				print("-----------------------------------")
				non_periodic_from_to_idx=[]
				non_periodic_day_idx=[]
				non_periodic_data=[]
			curr_month=month
			curr_month_data_per_weekday=[[],[],[],[],[],[],[]]
			curr_month_data_per_weekday_masks=[[],[],[],[],[],[],[]]
		if br==1:
			break
		print("Getting new date...",curr_date)
		filename1=load_folder+"/origins_dests_"+curr_date.strftime("%d_%m_%Y")+".npy"
		filename2=load_folder+"/info_"+curr_date.strftime("%d_%m_%Y")+".npz"
		day=curr_date.strftime("%d")
		day_name = curr_date.strftime("%A")
		day_index=days.index(day_name)
		today_data = np.load(filename1, allow_pickle=True)
		info = np.load(filename2, allow_pickle=True)
		print("processing")
		today_invalid_date = info["today_invalid_date"]
		today_invalid_boarding_code = info["today_invalid_boarding_code"]
		today_invalid_id = info["today_invalid_id"]
		today_invalid_disc = info["today_invalid_disc"]
		today_invalid_station = info["today_invalid_station"]
		today_unmatched_entries = info["today_unmatched_entries"]
		today_unmatched_exits = info["today_unmatched_exits"]
		today_category_entries = info["today_category_entries"]
		today_category_exits = info["today_category_exits"]
		today_same_station_tracks = info["today_same_station_tracks"]
		today_duplicates = info["today_duplicates"]
		today_almost_duplicates = info["today_almost_duplicates"]
		#### Distribute unmatched entries
		data_sum_by_row=np.sum(today_data,axis=3,keepdims=True)
		data_sum_by_row=np.broadcast_to(data_sum_by_row,today_data.shape)
		weights=today_data/data_sum_by_row
		weights[np.isnan(weights)]=1/70
		u_entries_expanded=np.broadcast_to(today_unmatched_entries[...,None],today_data.shape)
		additional_data=np.round(u_entries_expanded*weights).astype(np.int32)
		today_data+=additional_data
		####
		#### Distribute unmatched exits
		data_sum_by_col=np.sum(today_data,axis=2,keepdims=True)
		data_sum_by_col=np.broadcast_to(data_sum_by_col,today_data.shape)
		weights=today_data/data_sum_by_col
		weights[np.isnan(weights)]=1/70
		u_exits_expanded=np.broadcast_to(today_unmatched_exits[...,None,:],today_data.shape)
		additional_data=np.round(u_exits_expanded*weights).astype(np.int32)
		today_data+=additional_data
		###illegal boardings
		today_data+=np.round(today_data*illegal_boarding_rate).astype(np.int32)
		year=curr_date.strftime("%Y")
		data_mask=np.ones(today_data.shape)
		skip_fl=0
		if curr_date.strftime("%d/%m/%Y") in excluded_dates:
			curr_date+=timedelta(days=1)
			continue
		if curr_date.strftime("%d/%m/%Y") in non_periodic_special_dates:
			pr_idx=non_periodic_special_dates.index(curr_date.strftime("%d/%m/%Y"))
			spec_time=special_hours[pr_idx]
			h_idx=spec_time-hour_zero
			data_mask[h_idx-1:h_idx+special_event_duration-1]=0
			non_periodic_data.append(today_data[h_idx-1:h_idx+special_event_duration-1])
			non_periodic_day_idx.append(days.index(day_name))
			non_periodic_from_to_idx.append((h_idx-1,h_idx+special_event_duration-1))
		if curr_date.strftime("%d/%m/%Y") in fw[int(year)-init_year]:
			fw_data[int(day)-1].append(today_data)
			fw_data_masks[int(day)-1].append(data_mask)
			skip_fl=1
		if curr_date.strftime("%d/%m/%Y") in lw[int(year)-init_year]:
			lw_data[int(day)-24].append(today_data)
			lw_data_masks[int(day)-24].append(data_mask)
			skip_fl=1
		if curr_date.strftime("%d/%m/%Y") in mv[int(year)-init_year]:
			mv_idx=mv[int(year)-init_year].index(curr_date.strftime("%d/%m/%Y"))
			mv_data[mv_idx].append(today_data)
			mv_data_masks[mv_idx].append(data_mask)
			skip_fl=1
		if curr_date.strftime("%d/%m/%Y") in vp[int(year)-init_year]:
			vp_idx=vp[int(year)-init_year].index(curr_date.strftime("%d/%m/%Y"))
			vp_data[vp_idx].append(today_data)
			vp_data_masks[vp_idx].append(data_mask)
			skip_fl=1
		if curr_date.strftime("%d/%m/%Y") in kd:
			kd_data.append(today_data*data_mask)
			kd_data_masks.append(data_mask)
			skip_fl=1
		if skip_fl==0:
			curr_month_data_per_weekday[day_index].append(today_data)
			curr_month_data_per_weekday_masks[day_index].append(data_mask)
			curr_all_data_per_weekday[day_index].append(today_data)
			curr_all_data_per_weekday_masks[day_index].append(data_mask)
		curr_date+=timedelta(days=1)
	avg_event_dev=total_event_dev_sum/total_event_dev_sum_mask
	avg_fw=[]
	for i in range(len(fw_data)):
		tot_data=np.zeros([24*30,70,70])
		tot_mask=np.zeros([24*30,70,70])
		for j in range(len(fw_data[i])):
			c_dt=fw_data[i][j].reshape(-1,70,70)
			c_msk=fw_data_masks[i][j].reshape(-1,70,70)
			tot_data+=c_dt
			tot_mask+=c_msk
		avg_fw.append(tot_data/tot_mask)
	avg_lw=[]
	for i in range(len(lw_data)):
		tot_data=np.zeros([24*30,70,70])
		tot_mask=np.zeros([24*30,70,70])
		for j in range(len(lw_data[i])):
			c_dt=lw_data[i][j].reshape(-1,70,70)
			c_msk=lw_data_masks[i][j].reshape(-1,70,70)
			tot_data+=c_dt
			tot_mask+=c_msk
		avg_lw.append(tot_data/tot_mask)
	avg_mv=[]
	for i in range(len(mv_data)):
		tot_data=np.zeros([24*30,70,70])
		tot_mask=np.zeros([24*30,70,70])
		for j in range(len(mv_data[i])):
			c_dt=mv_data[i][j].reshape(-1,70,70)
			c_msk=mv_data_masks[i][j].reshape(-1,70,70)
			tot_data+=c_dt
			tot_mask+=c_msk
		avg_mv.append(tot_data/tot_mask)
	avg_vp=[]
	for i in range(len(vp_data)):
		tot_data=np.zeros([24*30,70,70])
		tot_mask=np.zeros([24*30,70,70])
		for j in range(len(vp_data[i])):
			c_dt=vp_data[i][j].reshape(-1,70,70)
			c_msk=vp_data_masks[i][j].reshape(-1,70,70)
			tot_data+=c_dt
			tot_mask+=c_msk
		avg_vp.append(tot_data/tot_mask)
	tot_data=np.zeros([24*30,70,70])
	tot_mask=np.zeros([24*30,70,70])
	for i in range(len(kd_data)):
			c_dt=kd_data[i].reshape(-1,70,70)
			c_msk=kd_data_masks[i].reshape(-1,70,70)
			tot_data+=c_dt
			tot_mask+=c_msk
	avg_kd=tot_data/tot_mask
	all_avg=[]
	all_avg_masks=[]
	all_min=[]
	all_max=[]
	for i in range(7):
		base_mask=np.zeros([24,30,70,70])
		base_data=np.zeros([24,30,70,70])
		all_weekday_min=np.ones([24,30,70,70])*np.inf
		all_weekday_max=-np.ones([24,30,70,70])*np.inf
		for j in range(len(curr_all_data_per_weekday[i])):
			curr_dt=curr_all_data_per_weekday[i][j]*curr_all_data_per_weekday_masks[i][j]
			#curr_month_data_per_weekday[np.isnan(curr_month_data_per_weekday)]=0
			all_weekday_min=np.minimum(all_weekday_min,curr_dt)
			all_weekday_max=np.maximum(all_weekday_max,curr_dt)
			base_data+=curr_dt
			base_mask+=curr_all_data_per_weekday_masks[i][j]
		all_min.append(all_weekday_min)
		all_max.append(all_weekday_max)
		all_weekday_avg=base_data/base_mask
		all_avg.append(all_weekday_avg)
	return (all_min, all_max, all_avg, all_avg_masks, avg_event_dev, avg_fw, avg_lw, avg_mv, avg_vp, avg_kd)

def select_graph_to_display(
	date_from,
	date_to,
	non_periodic_special_dates,
	special_hours,
	excluded_dates,
	load_folder,
	save_folder,
	graph_type="all_average",
	day=1,
	month=-1,
	year=-1,
	station=-1,
	hour_zero=4,
	special_event_duration=5,
	periodic_special_dates=None,
	illegal_boarding_rate=0.1
):
	days=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
	all_min, all_max, all_avg, all_avg_masks, avg_event_dev, avg_fw, avg_lw, avg_mv, avg_vp, avg_kd=create_plot_arrays(
		curr_date=date_from,
		end_date=date_to,
		non_periodic_special_dates=non_periodic_special_dates,
		special_hours=special_hours,
		excluded_dates=excluded_dates,
		load_folder=load_folder,
		save_folder=save_folder,
		hour_zero=hour_zero,
		special_event_duration=special_event_duration,
		illegal_boarding_rate=illegal_boarding_rate,
	)
	if graph_type=="all_average":
		r_tmp=all_avg[day].reshape((24*30,70,70))
		if station==-1:
			result=np.sum(r_tmp,axis=(1,2))
		else:
			result=np.sum(r_tmp,axis=1)[:,station]
	elif graph_type=="all_min":
		r_tmp=all_min[day].reshape((24*30,70,70))
		if station==-1:
			result=np.sum(r_tmp,axis=(1,2))
		else:
			result=np.sum(r_tmp,axis=1)[:,station]
	elif graph_type=="all_max":
		r_tmp=all_max[day].reshape((24*30,70,70))
		if station==-1:
			result=np.sum(r_tmp,axis=(1,2))
		else:
			result=np.sum(r_tmp,axis=1)[:,station]
	elif graph_type=="month_day_avg":
		print(save_folder+"/"+year+"/"+month+"/"+days[day]+"/data_avg.npy")
		data=np.load(save_folder+"/"+year+"/"+month+"/"+days[day]+"/data_avg.npy")
		print("loaded data")
		r_tmp=data[day].reshape((24*30,70,70))
		if station==-1:
			result=np.sum(r_tmp,axis=(1,2))
		else:
			result=np.sum(r_tmp,axis=1)[:,station]
	elif graph_type=="month_day_min":
		data=np.load(save_folder+"/"+year+"/"+month+"/"+days[day]+"/data_min.npy")
		r_tmp=data[day].reshape((24*30,70,70))
		if station==-1:
			result=np.sum(r_tmp,axis=(1,2))
		else:
			result=np.sum(r_tmp,axis=1)[:,station]
	elif graph_type=="month_day_max":
		data=np.load(save_folder+"/"+year+"/"+month+"/"+days[day]+"/data_max.npy")
		r_tmp=data[day].reshape((24*30,70,70))
		if station==-1:
			result=np.sum(r_tmp,axis=(1,2))
		else:
			result=np.sum(r_tmp,axis=1)[:,station]
	elif graph_type=="event_deviation":
		r_tmp=avg_event_dev.reshape(-1,70,70)
		if station==-1:
			result=np.sum(r_tmp,axis=(1,2))
		else:
			result=np.sum(r_tmp,axis=1)[:,station]
	elif graph_type=="fw":
		r_tmp=avg_fw
		if station==-1:
			result=[]
			for i in range(len(r_tmp)):
				result.append(np.sum(r_tmp[i],axis=(1,2)))
		else:
			result=[]
			for i in range(len(avg_fw)):
				result.append(np.sum(r_tmp,axis=1)[:,station])
	elif graph_type=="lw":
		r_tmp=avg_lw
		if station==-1:
			result=[]
			for i in range(len(r_tmp)):
				result.append(np.sum(r_tmp[i],axis=(1,2)))
		else:
			result=[]
			for i in range(len(avg_fw)):
				result.append(np.sum(r_tmp,axis=1)[:,station])
	elif graph_type=="mv":
		r_tmp=avg_mv
		if station==-1:
			result=[]
			for i in range(len(r_tmp)):
				result.append(np.sum(r_tmp[i],axis=(1,2)))
		else:
			result=[]
			for i in range(len(avg_fw)):
				result.append(np.sum(r_tmp,axis=1)[:,station])
	elif graph_type=="vp":
		r_tmp=avg_vp
		if station==-1:
			result=[]
			for i in range(len(r_tmp)):
				result.append(np.sum(r_tmp[i],axis=(1,2)))
		else:
			result=[]
			for i in range(len(avg_fw)):
				result.append(np.sum(r_tmp,axis=1)[:,station])
	elif graph_type=="kd":
		r_tmp=avg_kd
		if station==-1:
			result=np.sum(r_tmp,axis=(1,2))
		else:
			result=np.sum(r_tmp,axis=1)[:,station]
	print(result)
	return result

def display_extra_info(date_from,date_to,load_folder):
	l1=['[01011] ΠΕΙΡΑΙΑΣ','[01012] ΦΑΛΗΡΟ','[01013] ΜΟΣΧΑTΟ','[01014] KΑΛΛΙΘΕΑ','[01015] TΑΥΡΟΣ','[01016] ΠΕTΡΑΛΩΝΑ','[01017] ΘΗΣΕΙΟ','[01018] ΜΟΝΑΣTΗΡΑKΙ','[01019] ΟΜOΝΟΙΑ','[01020] ΒΙKTΩΡΙΑ','[01021] ΑTTΙKΗ','[01022] ΑΓΙΟΣ ΝΙKOΛΑΟΣ','[01023] KΑTΩ ΠΑTΗΣΙΑ','[01024] ΑΓΙΟΣ ΕΛΕΥΘΕΡΙΟΣ','[01025] ΑΝΩ ΠΑTΗΣΙΑ','[01026] ΠΕΡΙΣΣOΣ','[01027] ΠΕΥKΑKΙΑ','[01028] ΝΕΑ ΙΩΝΙΑ','[01029] ΗΡΑKΛΕΙΟ','[01030] ΕΙΡΗΝΗ','[01074] ΝΕΡΑTΖΙΩTΙΣΣΑ','[01031] ΜΑΡΟΥΣΙ','[01032] KΑT','[01033] KΗΦΙΣΙΑ']
	l2=['[01034] ΑΝΘΟΥΠΟΛΗ','[01035] ΠΕΡΙΣTΕΡΙ','[01036] ΑΓΙΟΣ ΑΝTΩΝΙΟΣ','[01037] ΣΕΠOΛΙΑ','[01038] ΑTTΙKΗ','[01039] ΣTΑΘΜOΣ ΛΑΡΙΣΗΣ','[01040] ΜΕTΑΞΟΥΡΓΕΙΟ','[01076] ΟΜOΝΟΙΑ','[01041] ΠΑΝΕΠΙΣTΗΜΙΟ','[01042] ΣΥΝTΑΓΜΑ','[01043] ΑKΡOΠΟΛΗ','[01044] ΣΥΓΓΡΟΥ ΦΙΞ','[01045] ΝΕΟΣ KOΣΜΟΣ','[01046] ΑΓΙΟΣ ΙΩΑΝΝΗΣ','[01047] ΔΑΦΝΗ','[01048] ΑΓΙΟΣ ΔΗΜΗTΡΙΟΣ','[01049] ΗΛΙΟΥΠΟΛΗ','[01050] ΑΛΙΜΟΣ','[01051] ΑΡΓΥΡΟΥΠΟΛΗ','[01052] ΕΛΛΗΝΙKO']
	l3=['[01086] ΔΗΜΟΤΙΚΟ ΘΕΑΤΡΟ','[01085] ΠΕΙΡΑΙΑΣ','[01084] ΜΑΝΙΑΤΙΚΑ','[01083] ΝΙΚΑΙΑ','[01082] ΚΟΡΥΔΑΛΛΟΣ','[01081] ΑΓΙΑ ΒΑΡΒΑΡΑ','[01053] ΑΓΙΑ ΜΑΡΙΝΑ','[01054] ΑΙΓΑΛΕΩ','[01055] ΕΛΑΙΩΝΑΣ','[01056] KΕΡΑΜΕΙKOΣ','[01057] ΜΟΝΑΣTΗΡΑKΙ','[01059] ΕΥΑΓΓΕΛΙΣΜOΣ','[01060] ΜΕΓΑΡΟ ΜΟΥΣΙKΗΣ','[01061] ΑΜΠΕΛOKΗΠΟΙ','[01062] ΠΑΝOΡΜΟΥ','[01063] KΑTΕΧΑKΗ','[01064] ΕΘΝΙKΗ ΑΜΥΝΑ','[01065] ΧΟΛΑΡΓOΣ','[01066] ΝΟΜΙΣΜΑTΟKΟΠΕΙΟ','[01067] ΑΓΙΑ ΠΑΡΑΣKΕΥΗ','[01068] ΧΑΛΑΝΔΡΙ','[01069] ΔΟΥKΙΣΣΗΣ ΠΛΑKΕΝTΙΑΣ','[01080] ΠΑΛΛΗΝΗ','[01079] ΠΑΙΑΝΙΑ - KΑΝTΖΑ','[01078] KΟΡΩΠΙ','[01077] ΑΕΡΟΔΡΟΜΙΟ']
	all_names=l1+l2+l3
	curr_date=date_from
	sum_today_invalid_date=0
	sum_today_invalid_boarding_code=0
	sum_today_invalid_id=0
	sum_today_invalid_disc=0
	sum_today_invalid_station=0
	sum_today_unmatched_entries=np.zeros([24,30,70])
	sum_today_unmatched_exits=np.zeros([24,30,70])
	sum_today_same_station_tracks=np.zeros([70])
	sum_today_duplicates=np.zeros([70])
	sum_today_almost_duplicates=np.zeros([70])
	sum_today_category_entries=np.zeros([24,30,70,len(DISC_PROFILES)])
	sum_today_category_exits=np.zeros([24,30,70,len(DISC_PROFILES)])
	count=0
	while curr_date<=date_to:
		count+=1
		filename=load_folder+"/info_"+curr_date.strftime("%d_%m_%Y")+".npz"
		info = np.load(filename, allow_pickle=True)
		today_invalid_date = info["today_invalid_date"]
		sum_today_invalid_date+=today_invalid_date
		today_invalid_boarding_code = info["today_invalid_boarding_code"]
		sum_today_invalid_boarding_code+=today_invalid_boarding_code
		today_invalid_id = info["today_invalid_id"]
		sum_today_invalid_id+=today_invalid_id
		today_invalid_disc = info["today_invalid_disc"]
		sum_today_invalid_disc+=today_invalid_disc
		today_invalid_station = info["today_invalid_station"]
		sum_today_invalid_station+=today_invalid_station
		today_unmatched_entries = info["today_unmatched_entries"]
		sum_today_unmatched_entries+=today_unmatched_entries
		today_unmatched_exits = info["today_unmatched_exits"]
		sum_today_unmatched_exits+=today_unmatched_exits
		today_category_entries = info["today_category_entries"]
		sum_today_category_entries+=today_category_entries
		today_category_exits = info["today_category_exits"]
		sum_today_category_exits+=today_category_exits
		today_same_station_tracks = info["today_same_station_tracks"]
		sum_today_same_station_tracks+=today_same_station_tracks
		today_duplicates = info["today_duplicates"]
		sum_today_duplicates+=today_duplicates
		today_almost_duplicates = info["today_almost_duplicates"]
		sum_today_almost_duplicates+=today_almost_duplicates
		curr_date+=timedelta(days=1)
	sum_today_invalid_date/=count
	sum_today_invalid_boarding_code/=count
	sum_today_invalid_id/=count
	sum_today_invalid_disc/=count
	sum_today_invalid_station/=count
	sum_today_unmatched_entries/=count
	sum_today_unmatched_entries_sum=np.sum(sum_today_unmatched_entries, axis=(0,1))
	sum_today_unmatched_exits/=count
	sum_today_unmatched_exits_sum=np.sum(sum_today_unmatched_exits, axis=(0,1))
	sum_today_category_entries/=count
	sum_today_category_entries_sum=np.sum(sum_today_category_entries, axis=(0,1))
	sum_today_category_exits/=count
	sum_today_category_exits_sum=np.sum(sum_today_category_exits, axis=(0,1))
	sum_today_same_station_tracks/=count
	sum_today_duplicates/=count
	sum_today_almost_duplicates/=count
	return (sum_today_invalid_date, sum_today_invalid_boarding_code, sum_today_invalid_id, sum_today_invalid_disc, sum_today_invalid_station, sum_today_unmatched_entries_sum, sum_today_unmatched_exits_sum, sum_today_category_entries_sum, sum_today_category_exits_sum, sum_today_same_station_tracks, sum_today_duplicates, sum_today_almost_duplicates)