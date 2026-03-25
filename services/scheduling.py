import numpy as np
from pyscipopt import Model, quicksum, SCIP_PARAMSETTING
import matplotlib.pyplot as plt


def calc_capacity_need_per_station_at_time_t(demand_arr, times_between_stations, init_time):
    time_slice_sec = 3600 * 24 / demand_arr.shape[0]
    capacity_need = np.zeros(demand_arr.shape[1])
    t_idx = init_time
    if init_time + round(np.sum(times_between_stations) / time_slice_sec) >= demand_arr.shape[0]:
        return capacity_need
    for i in range(demand_arr.shape[1]):
        if i != 0:
            capacity_need[i] += capacity_need[i - 1]  # previously boarded passengers
        for j in range(i + 1, demand_arr.shape[1]):
            capacity_need[i] += demand_arr[round(t_idx), i, j]  # added passengers
            capacity_need[j] -= demand_arr[round(t_idx), i, j]  # balance exits
        if i != demand_arr.shape[1] - 1:
            t_idx += times_between_stations[i] / time_slice_sec
    return capacity_need


def calc_capacity_need_per_station_at_time_t_opposite(demand_arr, times_between_stations, init_time):
    time_slice_sec = 3600 * 24 / demand_arr.shape[0]
    capacity_need = np.zeros(demand_arr.shape[1])
    t_idx = init_time
    if init_time + round(np.sum(times_between_stations) / time_slice_sec) >= demand_arr.shape[0]:
        return capacity_need
    for i in range(demand_arr.shape[1] - 1, -1, -1):
        if i != demand_arr.shape[1] - 1:
            capacity_need[i] += capacity_need[i + 1]  # previously boarded passengers
        for j in range(i - 1, -1, -1):
            capacity_need[i] += demand_arr[round(t_idx), i, j]  # added passengers
            capacity_need[j] -= demand_arr[round(t_idx), i, j]  # balance exits
        if i != 0:
            t_idx += times_between_stations[i - 1] / time_slice_sec
    return capacity_need


def convert_demand_to_correct_time_slice(two_min_demand_arr, time_slice_sec):
    unified_time_demand_arr = two_min_demand_arr.reshape(24 * 30, two_min_demand_arr.shape[2],
                                                         two_min_demand_arr.shape[3])
    final_arr = np.zeros((24 * 3600 // int(time_slice_sec), two_min_demand_arr.shape[2], two_min_demand_arr.shape[3]))
    end_2_min_idx = 0
    for i in range(24 * 3600 // int(time_slice_sec)):
        start_2_min_idx = end_2_min_idx
        end_2_min_idx = start_2_min_idx + time_slice_sec / 120
        start_fraction = start_2_min_idx - int(start_2_min_idx)
        end_fraction = end_2_min_idx - int(end_2_min_idx)
        if int(start_2_min_idx) != int(end_2_min_idx):
            if int(end_2_min_idx) != len(unified_time_demand_arr):
                final_arr[i] = (1 - start_fraction) * unified_time_demand_arr[int(start_2_min_idx)] + end_fraction * \
                               unified_time_demand_arr[int(end_2_min_idx)]
            else:
                final_arr[i] = (1 - start_fraction) * unified_time_demand_arr[int(start_2_min_idx)]
            for j in range(1, int(end_2_min_idx) - int(start_2_min_idx)):
                final_arr[i] += unified_time_demand_arr[start_2_min_idx + j]
        else:
            final_arr[i] = (end_2_min_idx - start_2_min_idx) * unified_time_demand_arr[int(start_2_min_idx)]
    return final_arr


def schedule(
        demand_arr,
        times_between_stations,
        times_between_stations_opposite,  # positions are the same - times_between_stations_opposite[0]:t1->0
        initial_state,
        max_train_num_at_ends,
        min_t_between_trains,  # seconds
        max_wait_unit_slices,  # slices
        min_rotation_time,
        forbidden_slices_idx,
        forbidden_slices_opposite_idx,
        max_capacity,
        a,  # waiting minimization importance
        b,  # total scheduled capacity minimization importance
        time_limit=300,
        group_by_optim=20,
        phase_out_seconds=3600
):
    t_unit = min_t_between_trains // 2
    phase_out_slices = phase_out_seconds // t_unit
    current_state = initial_state
    num_slices = demand_arr.shape[0]
    c = np.zeros((num_slices, demand_arr.shape[2]))
    c1 = np.zeros((num_slices, demand_arr.shape[2]))
    forbidden_slices = np.zeros(num_slices)
    forbidden_slices_opposite = np.zeros(num_slices)
    forbidden_slices[forbidden_slices_idx] = 1
    forbidden_slices_opposite[forbidden_slices_opposite_idx] = 1
    for i in range(num_slices):
        c[i] = calc_capacity_need_per_station_at_time_t(demand_arr, times_between_stations, i)
        c1[i] = calc_capacity_need_per_station_at_time_t_opposite(demand_arr, times_between_stations_opposite, i)
    sum_c = np.zeros((num_slices, demand_arr.shape[2]))
    sum_c1 = np.zeros((num_slices, demand_arr.shape[2]))
    sum_c[0] = c[0]
    sum_c1[0] = c1[0]
    for i in range(1, num_slices):
        sum_c[i] = sum_c[i - 1] + c[i]
        sum_c1[i] = sum_c1[i - 1] + c1[i]
    sch = Model("scheduler")
    x = {i: sch.addVar(vtype="B", name=f"x[{i}]") for i in range(num_slices)}
    x1 = {i: sch.addVar(vtype="B", name=f"x1[{i}]") for i in range(num_slices)}  # opposite
    s = {i: sch.addVar(vtype="C", lb=0, ub=max_train_num_at_ends[0], name=f"s[{i}]") for i in
         range(num_slices)}  # trains waiting at start
    s1 = {i: sch.addVar(vtype="C", lb=0, ub=max_train_num_at_ends[1], name=f"s1[{i}]") for i in
          range(num_slices)}  # trains waiting at end
    for i in range(num_slices): sch.addCons(x[i] <= 1 - forbidden_slices[i], name=f"forbidden_constr[{i}]")
    for i in range(num_slices): sch.addCons(x1[i] <= 1 - forbidden_slices_opposite[i],
                                            name=f"forbidden_constr_opp[{i}]")
    d = sum(times_between_stations) // t_unit
    d1 = sum(times_between_stations_opposite) // t_unit
    print("Scheduling with max_wait_slices=", max_wait_unit_slices, ",phase out slices=", phase_out_slices,
          "and t_unit=", t_unit)
    if max_wait_unit_slices > 0:
        for i in range(max_wait_unit_slices, num_slices - phase_out_slices):
            sch.addCons(quicksum(x[j] for j in range(i - max_wait_unit_slices, i)) >= 1)
        for i in range(max_wait_unit_slices, num_slices - phase_out_slices):
            sch.addCons(quicksum(x1[j] for j in range(i - max_wait_unit_slices, i)) >= 1)
    for i in range(1, d1 + 1): sch.addCons(s[i] == s[i - 1] - x[i - 1])
    for i in range(d1 + 1, num_slices): sch.addCons(s[i] == s[i - 1] - x[i - 1] + x1[i - d1 - 1])
    for i in range(1, d + 1): sch.addCons(s1[i] == s1[i - 1] - x1[i - 1])
    for i in range(d + 1, num_slices): sch.addCons(s1[i] == s1[i - 1] - x1[i - 1] + x[i - d - 1])
    sch.addCons(s[0] == initial_state[0])
    sch.addCons(s1[0] == initial_state[1])
    # sch.addCons(s1[num_slices-1]+s[num_slices-1]==initial_state[1]+initial_state[0])
    sum_x_until_i = {i: sch.addVar(vtype="C", name=f"sum_x_until_i[{i}]") for i in range(num_slices)}
    sum_x1_until_i = {i: sch.addVar(vtype="C", name=f"sum_x1_until_i[{i}]") for i in range(num_slices)}
    sch.addCons(sum_x_until_i[0] == x[0])
    for i in range(1, num_slices): sch.addCons(sum_x_until_i[i] == sum_x_until_i[i - 1] + x[i])
    sch.addCons(sum_x1_until_i[0] == x1[0])
    for i in range(1, num_slices): sch.addCons(sum_x1_until_i[i] == sum_x1_until_i[i - 1] + x1[i])
    for i in range(num_slices - 1): sch.addCons(x[i] + x[i + 1] <= 1)
    for i in range(num_slices - 1): sch.addCons(x1[i] + x1[i + 1] <= 1)
    for i in range(num_slices): sch.addCons(x[i] <= s[i])
    for i in range(num_slices): sch.addCons(x1[i] <= s1[i])
    waiting = {i: sch.addVar(vtype="I", lb=0, name=f"waiting[{i}]") for i in range(num_slices // group_by_optim)}
    sch.addCons(waiting[0] == 0)
    for i in range(1, num_slices // group_by_optim): sch.addCons(
        waiting[i] >= waiting[i - 1] + np.max(sum_c[i * group_by_optim] - sum_c[(i - 1) * group_by_optim]) - (
                    sum_x_until_i[i * group_by_optim] - sum_x_until_i[
                (i - 1) * group_by_optim]) * max_capacity)  # approximation to avoid too many variables
    waiting_opposite = {i: sch.addVar(vtype="I", lb=0, name=f"waiting_opposite[{i}]") for i in
                        range(num_slices // group_by_optim)}
    sch.addCons(waiting_opposite[0] == 0)
    for i in range(1, num_slices // group_by_optim): sch.addCons(
        waiting_opposite[i] >= waiting_opposite[i - 1] + np.max(
            sum_c1[i * group_by_optim] - sum_c1[(i - 1) * group_by_optim]) - (
                    sum_x1_until_i[i * group_by_optim] - sum_x1_until_i[
                (i - 1) * group_by_optim]) * max_capacity)  # approximation to avoid too many variables
    sch.setObjective(quicksum(
        a * (waiting[i // group_by_optim] + waiting_opposite[i // group_by_optim]) / group_by_optim + b * (
                    x[i] + x1[i]) * max_capacity for i in range(num_slices)), "minimize")
    sch.setParam("limits/time", time_limit)
    sch.optimize()
    if sch.getStatus() == "optimal":
        x_values = [sch.getVal(x[i]) for i in range(num_slices)]
        x1_values = [sch.getVal(x1[i]) for i in range(num_slices)]
        return (sch.getStatus(), x_values, x1_values)
    elif sch.getStatus() == "timelimit":
        if sch.getNSols() > 0:
            x_values = [sch.getVal(x[i]) for i in range(num_slices)]
            x1_values = [sch.getVal(x1[i]) for i in range(num_slices)]
            return (sch.getStatus(), x_values, x1_values)
        else:
            return (sch.getStatus(), [], [])
    else:
        return (sch.getStatus(), [], [])


def find_closest_past_station(slices, times_between_stations, seconds_per_slice, opposite=0):
    if opposite == 1:
        for i in range(len(times_between_stations) - 1, -1, -1):
            if np.sum(times_between_stations[i:]) > slices * seconds_per_slice:
                return i + 1
        return 0
    for i in range(len(times_between_stations)):
        if np.sum(times_between_stations[:i + 1]) > slices * seconds_per_slice:
            return i
    return len(times_between_stations)


def split_table_by_line(inp_arr, early_green_late_red_omonoia_frac=0.5, late_green_late_red_omonoia_frac=0.5,
                        early_red_early_blue_synt_frac=0.5, late_red_early_green_omon=0.5,
                        early_blue_early_red_synt_frac=0.5, late_blue_late_green_monast_frac=0.5):
    l1 = ['[01011] ΠΕΙΡΑΙΑΣ', '[01012] ΦΑΛΗΡΟ', '[01013] ΜΟΣΧΑTΟ', '[01014] KΑΛΛΙΘΕΑ', '[01015] TΑΥΡΟΣ',
          '[01016] ΠΕTΡΑΛΩΝΑ', '[01017] ΘΗΣΕΙΟ', '[01018] ΜΟΝΑΣTΗΡΑKΙ', '[01019] ΟΜOΝΟΙΑ', '[01020] ΒΙKTΩΡΙΑ',
          '[01021] ΑTTΙKΗ', '[01022] ΑΓΙΟΣ ΝΙKOΛΑΟΣ', '[01023] KΑTΩ ΠΑTΗΣΙΑ', '[01024] ΑΓΙΟΣ ΕΛΕΥΘΕΡΙΟΣ',
          '[01025] ΑΝΩ ΠΑTΗΣΙΑ', '[01026] ΠΕΡΙΣΣOΣ', '[01027] ΠΕΥKΑKΙΑ', '[01028] ΝΕΑ ΙΩΝΙΑ', '[01029] ΗΡΑKΛΕΙΟ',
          '[01030] ΕΙΡΗΝΗ', '[01074] ΝΕΡΑTΖΙΩTΙΣΣΑ', '[01031] ΜΑΡΟΥΣΙ', '[01032] KΑT', '[01033] KΗΦΙΣΙΑ']
    l2 = ['[01034] ΑΝΘΟΥΠΟΛΗ', '[01035] ΠΕΡΙΣTΕΡΙ', '[01036] ΑΓΙΟΣ ΑΝTΩΝΙΟΣ', '[01037] ΣΕΠOΛΙΑ', '[01038] ΑTTΙKΗ',
          '[01039] ΣTΑΘΜOΣ ΛΑΡΙΣΗΣ', '[01040] ΜΕTΑΞΟΥΡΓΕΙΟ', '[01076] ΟΜOΝΟΙΑ', '[01041] ΠΑΝΕΠΙΣTΗΜΙΟ',
          '[01042] ΣΥΝTΑΓΜΑ', '[01043] ΑKΡOΠΟΛΗ', '[01044] ΣΥΓΓΡΟΥ ΦΙΞ', '[01045] ΝΕΟΣ KOΣΜΟΣ', '[01046] ΑΓΙΟΣ ΙΩΑΝΝΗΣ',
          '[01047] ΔΑΦΝΗ', '[01048] ΑΓΙΟΣ ΔΗΜΗTΡΙΟΣ', '[01049] ΗΛΙΟΥΠΟΛΗ', '[01050] ΑΛΙΜΟΣ', '[01051] ΑΡΓΥΡΟΥΠΟΛΗ',
          '[01052] ΕΛΛΗΝΙKO']
    l3 = ['[01086] ΔΗΜΟΤΙΚΟ ΘΕΑΤΡΟ', '[01085] ΠΕΙΡΑΙΑΣ', '[01084] ΜΑΝΙΑΤΙΚΑ', '[01083] ΝΙΚΑΙΑ', '[01082] ΚΟΡΥΔΑΛΛΟΣ',
          '[01081] ΑΓΙΑ ΒΑΡΒΑΡΑ', '[01053] ΑΓΙΑ ΜΑΡΙΝΑ', '[01054] ΑΙΓΑΛΕΩ', '[01055] ΕΛΑΙΩΝΑΣ', '[01056] KΕΡΑΜΕΙKOΣ',
          '[01057] ΜΟΝΑΣTΗΡΑKΙ', '[01059] ΕΥΑΓΓΕΛΙΣΜOΣ', '[01060] ΜΕΓΑΡΟ ΜΟΥΣΙKΗΣ', '[01061] ΑΜΠΕΛOKΗΠΟΙ',
          '[01062] ΠΑΝOΡΜΟΥ', '[01063] KΑTΕΧΑKΗ', '[01064] ΕΘΝΙKΗ ΑΜΥΝΑ', '[01065] ΧΟΛΑΡΓOΣ', '[01066] ΝΟΜΙΣΜΑTΟKΟΠΕΙΟ',
          '[01067] ΑΓΙΑ ΠΑΡΑΣKΕΥΗ', '[01068] ΧΑΛΑΝΔΡΙ', '[01069] ΔΟΥKΙΣΣΗΣ ΠΛΑKΕΝTΙΑΣ', '[01080] ΠΑΛΛΗΝΗ',
          '[01079] ΠΑΙΑΝΙΑ - KΑΝTΖΑ', '[01078] KΟΡΩΠΙ', '[01077] ΑΕΡΟΔΡΟΜΙΟ']
    all_names = l1 + l2 + l3
    line_1 = inp_arr[:, :len(l1), :len(l1)].copy()
    line_2 = inp_arr[:, len(l1):len(l1 + l2), len(l1):len(l1 + l2)].copy()
    line_3 = inp_arr[:, len(l1 + l2):, len(l1 + l2):].copy()
    line_3 = np.insert(line_3, 11, 0, axis=1)
    line_3 = np.insert(line_3, 11, 0, axis=2)
    l3_new = ['[01086] ΔΗΜΟΤΙΚΟ ΘΕΑΤΡΟ', '[01085] ΠΕΙΡΑΙΑΣ', '[01084] ΜΑΝΙΑΤΙΚΑ', '[01083] ΝΙΚΑΙΑ',
              '[01082] ΚΟΡΥΔΑΛΛΟΣ', '[01081] ΑΓΙΑ ΒΑΡΒΑΡΑ', '[01053] ΑΓΙΑ ΜΑΡΙΝΑ', '[01054] ΑΙΓΑΛΕΩ',
              '[01055] ΕΛΑΙΩΝΑΣ', '[01056] KΕΡΑΜΕΙKOΣ', '[01057] ΜΟΝΑΣTΗΡΑKΙ', '[01042] ΣΥΝTΑΓΜΑ',
              '[01059] ΕΥΑΓΓΕΛΙΣΜOΣ', '[01060] ΜΕΓΑΡΟ ΜΟΥΣΙKΗΣ', '[01061] ΑΜΠΕΛOKΗΠΟΙ', '[01062] ΠΑΝOΡΜΟΥ',
              '[01063] KΑTΕΧΑKΗ', '[01064] ΕΘΝΙKΗ ΑΜΥΝΑ', '[01065] ΧΟΛΑΡΓOΣ', '[01066] ΝΟΜΙΣΜΑTΟKΟΠΕΙΟ',
              '[01067] ΑΓΙΑ ΠΑΡΑΣKΕΥΗ', '[01068] ΧΑΛΑΝΔΡΙ', '[01069] ΔΟΥKΙΣΣΗΣ ΠΛΑKΕΝTΙΑΣ', '[01080] ΠΑΛΛΗΝΗ',
              '[01079] ΠΑΙΑΝΙΑ - KΑΝTΖΑ', '[01078] KΟΡΩΠΙ', '[01077] ΑΕΡΟΔΡΟΜΙΟ']
    for i in range(inp_arr.shape[0]):
        for j in range(len(all_names)):
            for k in range(len(all_names)):
                src = all_names[j]
                dst = all_names[k]
                # print("Init:",src,"->",dst)
                if src == '[01018] ΜΟΝΑΣTΗΡΑKΙ':
                    if dst not in l1:
                        if dst in l3_new:
                            line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index(dst)] += inp_arr[i][j][k]
                        # print("adding l3 monastiraki ->",dst)
                        elif dst in l2 and (l2.index(dst) >= 10):
                            line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += \
                            inp_arr[i][j][k]
                            line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][k]
                        # print("adding l3 monastiraki -> syntagma +++ l2 syntagma ->",dst)
                        elif dst in l2 and l2.index(dst) <= 6:
                            line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                            line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][k]
                        # print("adding l1",src,"-> omonoia +++ l2 omonoia ->",dst)
                        elif dst in l2 and l2.index(dst) == 8:
                            line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += \
                            inp_arr[i][j][k] * 0.5
                            line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][k] * 0.5
                            # print("adding (0.5) l3 monastiraki -> syntagma +++ l2 syntagma ->",dst)
                            line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k] * 0.5
                            line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][k] * 0.5
                        # print("adding (0.5) l1",src,"-> omonoia +++ l2 omonoia ->",dst)
                        elif dst == '[01076] ΟΜOΝΟΙΑ':
                            line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                elif src == '[01057] ΜΟΝΑΣTΗΡΑKΙ':
                    if dst not in l3:
                        if dst in l1:
                            line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index(dst)] += inp_arr[i][j][k]
                        # print("adding l1 monastiraki ->",dst)
                        if dst in l3_new:  # syntagma
                            line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index(dst)] += inp_arr[i][j][k]
                        # print("adding l3 monastiraki ->",dst)
                        elif dst in l2 and (l2.index(dst) >= 10):
                            line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += \
                                inp_arr[i][j][k]
                            line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][k]
                        # print("adding l3 monastiraki -> syntagma +++ l2 syntagma ->",dst)
                        elif dst in l2 and l2.index(dst) <= 6:
                            line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                            line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][k]
                        # print("adding l1 monastiraki -> omonoia +++ l2 omonoia ->",dst)
                        elif dst in l2 and l2.index(dst) == 8:
                            line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += \
                                inp_arr[i][j][k] * 0.5
                            line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][k] * 0.5
                            # print("adding (0.5) l3 monastiraki -> syntagma +++ l2 syntagma ->",dst)
                            line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][
                                                                                                           k] * 0.5
                            line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][k] * 0.5
                        # print("adding (0.5) l1",src,"-> omonoia +++ l2 omonoia ->",dst)
                        elif dst == '[01076] ΟΜOΝΟΙΑ':
                            line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                    # print("adding l1 monastiraki -> omonoia ")
                elif src == '[01019] ΟΜOΝΟΙΑ':
                    if dst not in l1:
                        if dst == '[01042] ΣΥΝTΑΓΜΑ':
                            line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                        # print("l2 omon syn")
                        elif dst in l3_new and l3_new.index(dst) >= 12:
                            line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                            line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index(dst)] += inp_arr[i][j][k]
                        # print("l2 omon syn +++ l3 syn ->",dst)
                        elif dst == '[01057] ΜΟΝΑΣTΗΡΑKΙ':
                            line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                        # print("l1 omon monast")
                        elif dst in l3_new and l3_new.index(dst) <= 9:
                            line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                            line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index(dst)] += inp_arr[i][j][k]
                        # print("l1 omon monast +++ l3 monast - >",dst)
                        elif dst in l2:
                            line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][k]
                    # print("l2 omon ->",dst)
                elif src == '[01076] ΟΜOΝΟΙΑ':
                    if dst not in l2:
                        if dst in l3_new and l3_new.index(dst) >= 12:
                            line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                            line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index(dst)] += inp_arr[i][j][k]
                        # print("l2 omon syn +++ l3 syn ->",dst)
                        elif dst == '[01018] ΜΟΝΑΣTΗΡΑKΙ':
                            line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                        # print("l1 omon monast")
                        elif dst in l3_new and l3_new.index(dst) <= 9:
                            line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                            line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index(dst)] += inp_arr[i][j][k]
                        # print("l1 omon monast +++ l3 monast - >",dst)
                        elif dst in l1:
                            line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index(dst)] += inp_arr[i][j][k]
                    # print("l2 omon ->",dst)
                elif src == '[01042] ΣΥΝTΑΓΜΑ':
                    if dst not in l2:
                        if dst in l3_new:
                            line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index(dst)] += inp_arr[i][j][k]
                        # print("l3 syn ->",dst)
                        elif dst == '[01018] ΜΟΝΑΣTΗΡΑKΙ':
                            line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += \
                            inp_arr[i][j][k]
                        # print("l3 syn mon")
                        elif dst == '[01019] ΟΜOΝΟΙΑ':
                            line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                        # print("l2 syn omon")
                        elif dst in l1 and l1.index(dst) <= 6:
                            line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += \
                            inp_arr[i][j][k]
                            line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index(dst)] += inp_arr[i][j][k]
                        # print("l3 syn monast +++ l1 monast->",dst)
                        elif dst in l1 and l1.index(dst) >= 9:
                            line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                            line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index(dst)] += inp_arr[i][j][k]
                    # print("l2 syn omon +++ l1 omon ->",dst)
                elif src in l1 and l1.index(src) <= 6:  # πειραιας εως και θησείο
                    if dst in l3 and (
                            l3.index(dst) <= 9 or l3.index(dst) >= 11):  # δθ εως και κεραμεικό - ευαγγελισμος εως τερμα
                        line_1[i][l1.index(src)][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                        line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index(dst)] += inp_arr[i][j][k]
                    # print("l1",src,"-> monast +++ l3 monast ->",dst)
                    if dst in l2 and (
                            l2.index(dst) <= 6 or l2.index(dst) == 8):  # ανθούπολη εως και μεταξουργείο ή πανεπιστήμιο
                        line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                        line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][k]
                    # print("l1",src,"-> omon +++ l2 omon ->",dst)
                    if dst in l2 and (l2.index(dst) >= 10):  # ακρόπολη-τερμα
                        line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][
                                                                                     k] * early_green_late_red_omonoia_frac
                        line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][
                                                                                     k] * early_green_late_red_omonoia_frac
                        # print("l1",src,"-> omon +++ l2 omon ->",dst)
                        line_1[i][l1.index(src)][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k] * (
                                1 - early_green_late_red_omonoia_frac)
                        line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += \
                        inp_arr[i][j][k] * (1 - early_green_late_red_omonoia_frac)
                        line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][k] * (
                                    1 - early_green_late_red_omonoia_frac)
                    # print("l1",src,"-> monast +++ l3 monast ->synt +++ l2 synt->",dst)
                    if dst == '[01076] ΟΜOΝΟΙΑ':
                        line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                    # print("l1",src,"->omon")
                    if dst == '[01057] ΜΟΝΑΣTΗΡΑKΙ':
                        line_1[i][l1.index(src)][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                    # print("l1",src,"->monast")
                    if dst == '[01042] ΣΥΝTΑΓΜΑ':
                        line_1[i][l1.index(src)][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                        line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += \
                        inp_arr[i][j][k]
                # print("l1",src,"->monast ++ l3 monast->synt")
                elif src in l1 and l1.index(src) >= 9:
                    if dst in l3 and (l3.index(dst) <= 9 or l3.index(dst) >= 11):
                        line_1[i][l1.index(src)][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                        line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index(dst)] += inp_arr[i][j][k]
                    # print("l1",src,"-> monast +++ l3 monast ->",dst)
                    if dst in l2 and (l2.index(dst) <= 6 or l2.index(dst) == 8):
                        line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                        line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][k]
                    # print("l1",src,"-> omon +++ l2 omon ->",dst)
                    if dst in l2 and (l2.index(dst) >= 10):  # ακρόπολη-τερμα
                        line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][
                                                                                     k] * late_green_late_red_omonoia_frac
                        line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][
                                                                                     k] * late_green_late_red_omonoia_frac
                        # print("l1",src,"-> omon +++ l2 omon ->",dst)
                        line_1[i][l1.index(src)][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k] * (
                                    1 - late_green_late_red_omonoia_frac)
                        line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += \
                            inp_arr[i][j][k] * (1 - late_green_late_red_omonoia_frac)
                        line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][k] * (
                                    1 - late_green_late_red_omonoia_frac)
                    # print("l1",src,"-> monast +++ l3 monast ->synt +++ l2 synt->",dst)
                    if dst == '[01076] ΟΜOΝΟΙΑ':
                        line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                    # print("l1",src,"->omon")
                    if dst == '[01057] ΜΟΝΑΣTΗΡΑKΙ':
                        line_1[i][l1.index(src)][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                    # print("l1",src,"->monast")
                    if dst == '[01042] ΣΥΝTΑΓΜΑ':
                        line_1[i][l1.index(src)][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k] * 0.5
                        line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += \
                            inp_arr[i][j][k] * 0.5
                        # print("l1",src,"-> monast +++ l3 monast ->",dst)
                        line_1[i][l1.index(src)][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k] * 0.5
                        line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k] * 0.5
                # print("l1",src,"-> omon +++ l2 omon ->",dst)
                elif src in l2 and (l2.index(src) <= 6 or l2.index(src) == 8):
                    if dst in l1 and dst != '[01018] ΜΟΝΑΣTΗΡΑKΙ' and dst != '[01019] ΟΜOΝΟΙΑ':
                        line_2[i][l2.index(src)][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                        line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index(dst)] += inp_arr[i][j][k]
                    # print("l2",src,"-> omon +++ l1 omon ->",dst)
                    if dst in l3 and l3.index(dst) >= 11:
                        line_2[i][l2.index(src)][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                        line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index(dst)] += inp_arr[i][j][k]
                    # print("l2",src,"-> synt +++ l3 synt ->",dst)
                    if dst in l3 and l3.index(dst) <= 9:
                        line_2[i][l2.index(src)][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][
                                                                                      k] * early_red_early_blue_synt_frac
                        line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index(dst)] += inp_arr[i][j][
                                                                                              k] * early_red_early_blue_synt_frac
                        # print("l2",src,"-> synt +++ l3 synt ->",dst)
                        line_2[i][l2.index(src)][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k] * (
                                1 - early_red_early_blue_synt_frac)
                        line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k] * (
                                1 - early_red_early_blue_synt_frac)
                        line_3[i][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')][l3_new.index(dst)] += inp_arr[i][j][k] * (
                                1 - early_red_early_blue_synt_frac)
                    # print("l2",src,"-> omon +++ l1 omon ->monast +++ l3 monast->",dst)
                    if dst == '[01019] ΟΜOΝΟΙΑ':
                        line_2[i][l2.index(src)][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                    # print("l2",src,"->omon")
                    if dst == '[01018] ΜΟΝΑΣTΗΡΑKΙ' or dst == '[01057] ΜΟΝΑΣTΗΡΑKΙ':
                        line_2[i][l2.index(src)][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k] * 0.5
                        line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][
                                                                                                       k] * 0.5
                        # print("l2",src,"-> omon +++ l1 omon ->",dst)
                        line_2[i][l2.index(src)][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k] * 0.5
                        line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += \
                        inp_arr[i][j][k] * 0.5
                # print("l2",src,"-> synt +++ l3 synt ->",dst)
                elif src in l2 and (l2.index(src) >= 10):
                    if dst in l3 and dst != '[01042] ΣΥΝTΑΓΜΑ':
                        line_2[i][l2.index(src)][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                        line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index(dst)] += inp_arr[i][j][k]
                    # print("l2",src,"-> synt +++ l3 synt ->",dst)
                    if dst in l1 and l1.index(dst) >= 9:
                        line_2[i][l2.index(src)][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                        line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index(dst)] += inp_arr[i][j][k]
                    # print("l2",src,"-> omon +++ l1 omon ->",dst)
                    if dst in l1 and l1.index(dst) <= 6:
                        line_2[i][l2.index(src)][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][
                                                                                     k] * late_red_early_green_omon
                        line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index(dst)] += inp_arr[i][j][
                                                                                     k] * late_red_early_green_omon
                        # print("l2",src,"-> omon +++ l1 omon ->",dst)
                        line_2[i][l2.index(src)][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k] * (
                                    1 - late_red_early_green_omon)
                        line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += \
                        inp_arr[i][j][k] * (1 - late_red_early_green_omon)
                        line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index(dst)] += inp_arr[i][j][k] * (
                                    1 - late_red_early_green_omon)
                    # print("l2",src,"-> synt +++ l3 synt ->monast +++ l1 monast->",dst)
                    if dst == '[01019] ΟΜOΝΟΙΑ':
                        line_2[i][l2.index(src)][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                    # print("l2",src,"->omon")
                    if dst == '[01018] ΜΟΝΑΣTΗΡΑKΙ':
                        line_2[i][l2.index(src)][l2.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                        line_3[i][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += \
                        inp_arr[i][j][k]
                # print("l2",src,"-> synt +++ l3 synt->monast")
                elif src in l3 and l3.index(src) <= 9:
                    if dst in l1 and dst != '[01018] ΜΟΝΑΣTΗΡΑKΙ' and dst != '[01019] ΟΜOΝΟΙΑ':
                        line_3[i][l3_new.index(src)][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                        line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index(dst)] += inp_arr[i][j][k]
                    # print("l3",src,"-> monast +++ l1 monast ->",dst)
                    if dst in l2 and (l2.index(dst) >= 10 or l2.index(dst) == 8):
                        line_3[i][l3_new.index(src)][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                        line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][k]
                    # print("l3",src,"-> synt +++ l2 synt ->",dst)
                    if dst in l2 and l2.index(dst) <= 6:
                        line_3[i][l3_new.index(src)][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][
                                                                                              k] * early_blue_early_red_synt_frac
                        line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][
                                                                                      k] * early_blue_early_red_synt_frac
                        # print("l3",src,"-> synt +++ l2 synt ->",dst)
                        line_3[i][l3_new.index(src)][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k] * (
                                    1 - early_blue_early_red_synt_frac)
                        line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k] * (
                                    1 - early_blue_early_red_synt_frac)
                        line_2[i][l2.index('[01076] ΟΜOΝΟΙΑ')][l2.index(dst)] += inp_arr[i][j][k] * (
                                    1 - early_blue_early_red_synt_frac)
                    # print("l3",src,"-> monast +++ l1 monast ->omon +++ l2 omon->",dst)
                    if dst == '[01018] ΜΟΝΑΣTΗΡΑKΙ':
                        line_3[i][l3_new.index(src)][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                    # print("l3",src,"->monast")
                    if dst == '[01019] ΟΜOΝΟΙΑ' or dst == '[01076] ΟΜOΝΟΙΑ':
                        line_3[i][l3_new.index(src)][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                        line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k]
                    # print("l3",src,"-> monast +++ l1 monast ->omon")
                    if dst == '[01042] ΣΥΝTΑΓΜΑ':
                        line_3[i][l3_new.index(src)][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                # print("l3",src,"->synt")
                elif src in l3 and l3.index(src) >= 11:
                    if dst in l2 and dst != '[01076] ΟΜOΝΟΙΑ' and dst != '[01042] ΣΥΝTΑΓΜΑ':
                        line_3[i][l3_new.index(src)][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                        line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index(dst)] += inp_arr[i][j][k]
                    # print("l3",src,"-> synt +++ l2 synt ->",dst)
                    if dst in l1 and l1.index(dst) <= 6:
                        line_3[i][l3_new.index(src)][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                        line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index(dst)] += inp_arr[i][j][k]
                    # print("l3",src,"-> monast +++ l1 monast ->",dst)
                    if dst in l1 and l1.index(dst) >= 9:
                        line_3[i][l3_new.index(src)][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][
                                                                                                 k] * late_blue_late_green_monast_frac
                        line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index(dst)] += inp_arr[i][j][
                                                                                         k] * late_blue_late_green_monast_frac
                        # print("l3",src,"-> monast +++ l1 monast ->",dst)
                        line_3[i][l3_new.index(src)][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k] * (
                                    1 - late_blue_late_green_monast_frac)
                        line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k] * (
                                1 - late_blue_late_green_monast_frac)
                        line_1[i][l1.index('[01019] ΟΜOΝΟΙΑ')][l1.index(dst)] += inp_arr[i][j][k] * (
                                    1 - late_blue_late_green_monast_frac)
                    # print("l3",src,"-> synt +++ l2 synt ->omon +++ l1 omon->",dst)
                    if dst == '[01018] ΜΟΝΑΣTΗΡΑKΙ':
                        line_3[i][l3_new.index(src)][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k]
                    # print("l3",src,"->monast")
                    if dst == '[01019] ΟΜOΝΟΙΑ' or dst == '[01076] ΟΜOΝΟΙΑ':
                        line_3[i][l3_new.index(src)][l3_new.index('[01057] ΜΟΝΑΣTΗΡΑKΙ')] += inp_arr[i][j][k] * 0.5
                        line_1[i][l1.index('[01018] ΜΟΝΑΣTΗΡΑKΙ')][l1.index('[01019] ΟΜOΝΟΙΑ')] += inp_arr[i][j][
                                                                                                       k] * 0.5
                        # print("l3",src,"-> monast +++ l1 monast ->omon")
                        line_3[i][l3_new.index(src)][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k] * 0.5
                        line_2[i][l2.index('[01042] ΣΥΝTΑΓΜΑ')][l2.index('[01076] ΟΜOΝΟΙΑ')] += inp_arr[i][j][k] * 0.5
                    # print("l3",src,"-> synt +++ l2 synt ->omon")
                    if dst == '[01042] ΣΥΝTΑΓΜΑ':
                        line_3[i][l3_new.index(src)][l3_new.index('[01042] ΣΥΝTΑΓΜΑ')] += inp_arr[i][j][k]
                # print("l3",src,"->synt")
    return (line_1, line_2, line_3)


def find_forbidden_slices(loop1, loop2, x, x1, times_between_stations, times_between_stations_opposite,
                          min_t_between_trains, forbidden, forbidden_opposite):  # loops->[start_idx,end_idx]
    # loop1 is scheduled, and we need to find forbidden indices for loop2
    o1 = 0
    o2 = 0
    if loop1[0] < loop2[0]:
        t_distance = sum(times_between_stations[loop1[0]:loop2[0]])
    else:
        o1 = 1
        t_distance = sum(times_between_stations[loop2[0]:loop1[0]])
    if loop1[1] < loop2[1]:
        t_distance_opposite = sum(times_between_stations_opposite[loop1[1]:loop2[1]])
    else:
        o2 = 1
        t_distance_opposite = sum(times_between_stations_opposite[loop2[1]:loop1[1]])
    slice_distance = t_distance / (min_t_between_trains / 2)
    slice_distance_opposite = t_distance_opposite / (min_t_between_trains / 2)
    if o1 == 0:
        for i in range(len(x)):
            if x[i] == 1:
                if i + int(slice_distance) - 2 >= 0 and i + int(slice_distance) - 2 not in forbidden:
                    forbidden.append(i + int(slice_distance) - 2)
                if i + int(slice_distance) - 1 >= 0 and i + int(slice_distance) - 1 not in forbidden:
                    forbidden.append(i + int(slice_distance) - 1)
                if i + int(slice_distance) <= len(x) - 1 and i + int(slice_distance) not in forbidden:
                    forbidden.append(i + int(slice_distance))
                if i + int(slice_distance) + 1 <= len(x) - 1 and i + int(slice_distance) + 1 not in forbidden:
                    forbidden.append(i + int(slice_distance) + 1)
                if i + int(slice_distance) + 2 <= len(x) - 1 and i + int(slice_distance) + 2 not in forbidden:
                    forbidden.append(i + int(slice_distance) + 2)
    elif o1 == 1:
        for i in range(len(x)):
            if x[i] == 1:
                if i - int(slice_distance) - 2 >= 0 and i - int(slice_distance) - 2 not in forbidden:
                    forbidden.append(i - int(slice_distance) - 2)
                if i - int(slice_distance) - 1 >= 0 and i - int(slice_distance) - 1 not in forbidden:
                    forbidden.append(i - int(slice_distance) - 1)
                if i - int(slice_distance) <= len(x) - 1 and i - int(slice_distance) not in forbidden:
                    forbidden.append(i - int(slice_distance))
                if i - int(slice_distance) + 1 <= len(x) - 1 and i - int(slice_distance) + 1 not in forbidden:
                    forbidden.append(i - int(slice_distance) + 1)
                if i - int(slice_distance) + 2 <= len(x) - 1 and i - int(slice_distance) + 2 not in forbidden:
                    forbidden.append(i - int(slice_distance) + 2)
    if o2 == 1:
        for i in range(len(x1)):
            if x1[i] == 1:
                if i + int(slice_distance_opposite) - 2 >= 0 and i + int(
                        slice_distance_opposite) - 2 not in forbidden_opposite:
                    forbidden_opposite.append(i + int(slice_distance_opposite) - 2)
                if i + int(slice_distance_opposite) - 1 >= 0 and i + int(
                        slice_distance_opposite) - 1 not in forbidden_opposite:
                    forbidden_opposite.append(i + int(slice_distance_opposite) - 1)
                if i + int(slice_distance_opposite) <= len(x) - 1 and i + int(
                        slice_distance_opposite) not in forbidden_opposite:
                    forbidden_opposite.append(i + int(slice_distance_opposite))
                if i + int(slice_distance_opposite) + 1 <= len(x) - 1 and i + int(
                        slice_distance_opposite) + 1 not in forbidden_opposite:
                    forbidden_opposite.append(i + int(slice_distance_opposite) + 1)
                if i + int(slice_distance_opposite) + 2 <= len(x) - 1 and i + int(
                        slice_distance_opposite) + 2 not in forbidden_opposite:
                    forbidden_opposite.append(i + int(slice_distance_opposite) + 2)
    elif o1 == 0:
        for i in range(len(x1)):
            if x1[i] == 1:
                if i - int(slice_distance_opposite) - 2 >= 0 and i - int(
                        slice_distance_opposite) - 2 not in forbidden_opposite:
                    forbidden_opposite.append(i - int(slice_distance_opposite) - 2)
                if i - int(slice_distance_opposite) - 1 >= 0 and i - int(
                        slice_distance_opposite) - 1 not in forbidden_opposite:
                    forbidden_opposite.append(i - int(slice_distance_opposite) - 1)
                if i - int(slice_distance_opposite) <= len(x) - 1 and i - int(
                        slice_distance_opposite) not in forbidden_opposite:
                    forbidden_opposite.append(i - int(slice_distance_opposite))
                if i - int(slice_distance_opposite) + 1 <= len(x) - 1 and i - int(
                        slice_distance_opposite) + 1 not in forbidden_opposite:
                    forbidden_opposite.append(i - int(slice_distance_opposite) + 1)
                if i - int(slice_distance_opposite) + 2 <= len(x) - 1 and i - int(
                        slice_distance_opposite) + 2 not in forbidden_opposite:
                    forbidden_opposite.append(i - int(slice_distance_opposite) + 2)
    return (forbidden, forbidden_opposite)


def schedule_with_loops(
        loops,  # [(idx_start,idx_end),...]
        line,
        demand_arr,
        times_between_stations,
        times_between_stations_opposite,  # positions are the same - times_between_stations_opposite[0]:t1->0
        initial_state,  # [(t11,t12),...]
        max_train_num_at_ends,  # [(m11,m12),...]
        min_t_between_trains,  # seconds
        max_wait_unit_slices,  # slices [w1,w2,...]
        min_rotation_time,
        forbidden_slices_idx,
        forbidden_slices_opposite_idx,
        max_capacity,
        a,  # waiting minimization importance
        b,  # total scheduled capacity minimization importance
        time_limit=300,
        phase_out_seconds=3600
):
    results = []
    by_line = split_table_by_line(demand_arr)
    input_arr = by_line[line - 1]
    stations_in_loop = []
    for l in loops:
        s = np.zeros(input_arr.shape[1])
        for i in range(input_arr.shape[1]):
            if i >= l[0] and i <= l[1]:
                s[i] = 1
        stations_in_loop.append(s)
    total_day_traffic = input_arr.sum(axis=0)
    dist = Model()
    d = {(i, j, k): dist.addVar(vtype="C", lb=0, ub=1, name=f"d[{i},{j},{k}]") for i in range(len(loops)) for j in
         range(total_day_traffic.shape[0]) for k in range(total_day_traffic.shape[1])}
    for i in range(len(loops)):
        for j in range(total_day_traffic.shape[0]):
            for k in range(total_day_traffic.shape[1]): dist.addCons(stations_in_loop[i][j] - d[i, j, k] >= 0)
    for i in range(len(loops)):
        for j in range(total_day_traffic.shape[0]):
            for k in range(total_day_traffic.shape[1]): dist.addCons(stations_in_loop[i][k] - d[i, j, k] >= 0)
    for j in range(total_day_traffic.shape[0]):
        for k in range(total_day_traffic.shape[1]): dist.addCons(quicksum(d[i, j, k] for i in range(len(loops))) == 1)
    m = {i: dist.addVar(vtype="C", lb=0, name=f"m[{i}]") for i in range(len(loops) - 1)}
    for i in range(len(loops) - 1): dist.addCons(m[i] >= quicksum(
        d[i, j, k] * total_day_traffic[j, k] for j in range(total_day_traffic.shape[0]) for k in
        range(total_day_traffic.shape[1])) / (initial_state[i][0] + initial_state[i][1]) - quicksum(
        d[i + 1, j, k] * total_day_traffic[j, k] for j in range(total_day_traffic.shape[0]) for k in
        range(total_day_traffic.shape[1])) / (initial_state[i + 1][0] + initial_state[i + 1][1]))
    for i in range(len(loops) - 1): dist.addCons(m[i] >= quicksum(
        d[i + 1, j, k] * total_day_traffic[j, k] for j in range(total_day_traffic.shape[0]) for k in
        range(total_day_traffic.shape[1])) / (initial_state[i + 1][0] + initial_state[i + 1][1]) - quicksum(
        d[i, j, k] * total_day_traffic[j, k] for j in range(total_day_traffic.shape[0]) for k in
        range(total_day_traffic.shape[1])) / (initial_state[i][0] + initial_state[i][1]))
    dist.setObjective(quicksum(m[i] for i in range(len(loops) - 1)), "minimize")
    dist.optimize()
    if dist.getStatus() == "optimal":
        d_np = np.array([[[dist.getVal(d[i, j, k]) for k in range(total_day_traffic.shape[1])] for j in
                          range(total_day_traffic.shape[0])] for i in range(len(loops))])

    for i in range(len(loops)):
        current_loop_input_array = (input_arr * d_np[i])[:, loops[i][0]:loops[i][1] + 1, loops[i][0]:loops[i][1] + 1]
        forbidden = []
        forbidden_opposite = []
        if i != 0:
            for j in range(i):
                forbidden, forbidden_opposite = find_forbidden_slices(loops[j], loops[i], results[j][0], results[j][1],
                                                                      times_between_stations,
                                                                      times_between_stations_opposite,
                                                                      min_t_between_trains, forbidden,
                                                                      forbidden_opposite)
        status, x, x1 = schedule(current_loop_input_array, times_between_stations[loops[i][0]:loops[i][1]],
                                 times_between_stations_opposite[loops[i][0]:loops[i][1]], initial_state[i],
                                 max_train_num_at_ends[i], min_t_between_trains, max_wait_unit_slices[i],
                                 min_rotation_time, forbidden_slices_idx, forbidden_slices_opposite_idx, max_capacity,
                                 a, b, time_limit, group_by_optim=20, phase_out_seconds=phase_out_seconds)
        if status != "optimal" and status != "timelimit":
            print("Unable to schedule. Status:", status)
        results.append((x, x1))
    return results


def simulate_loops(
        loops,
        demand_arr,
        x_scheduled,
        x1_scheduled,
        initial_state,
        min_t_between_trains,
        forbidden_slices_idx,
        forbidden_slices_opposite_idx,
        capacity,
        times_between_stations,
        times_between_stations_opposite,
        group_results_n_slices=5
):
    current_trains = []  # current_trains[i][j]=[n1,n2,...]: nk->number of total passengers when train j of loop i departs from station k
    for i in range(len(loops)):
        current_trains.append([])
    current_trains_loc = []  # current_trains_loc[i][j]: index of current station of train j of loop i
    for i in range(len(loops)):
        current_trains_loc.append([])
    current_trains_life_slices = []  # ij-th element: slices for which the train j of loop i exists - 0 for initial station/slice
    for i in range(len(loops)):
        current_trains_life_slices.append([])
    current_trains_opposite = []
    for i in range(len(loops)):
        current_trains_opposite.append([])
    current_trains_opposite_loc = []
    for i in range(len(loops)):
        current_trains_opposite_loc.append([])
    current_trains_opposite_life_slices = []
    for i in range(len(loops)):
        current_trains_opposite_life_slices.append([])
    remaining = np.zeros((demand_arr.shape[1], demand_arr.shape[1]))
    seconds_per_slice = 3600 * 24 / demand_arr.shape[0]
    print("simulator time unit:", seconds_per_slice)
    state = []
    total_new = np.zeros(demand_arr.shape[0] // group_results_n_slices)
    total_boarded = np.zeros(demand_arr.shape[0] // group_results_n_slices)
    total_moving_trains = []
    total_moving_trains_opposite = []
    for i in range(len(loops)):
        total_moving_trains.append(np.zeros(demand_arr.shape[0] // group_results_n_slices))
        total_moving_trains_opposite.append(np.zeros(demand_arr.shape[0] // group_results_n_slices))
    for l in loops:
        state.append([l[0], l[1]])
    for i in range(demand_arr.shape[0]):
        remaining += demand_arr[i]
        total_new[i // group_results_n_slices] += demand_arr[i].sum()
        for l in range(len(loops)):
            if x_scheduled[l][i] == 1:
                current_trains[l].append(np.zeros(demand_arr.shape[1]))
                current_trains_loc[l].append(-1)
                current_trains_life_slices[l].append(-1)
                state[l][0] -= 1
            if x1_scheduled[l][i] == 1:
                current_trains_opposite[l].append(np.zeros(demand_arr.shape[1]))
                current_trains_opposite_loc[l].append(-1)
                current_trains_opposite_life_slices[l].append(-1)
                state[l][1] -= 1
            total_moving_trains[l][i // group_results_n_slices] = len(current_trains[l])
            total_moving_trains_opposite[l][i // group_results_n_slices] = len(current_trains_opposite[l])
            trains_ended = 0
            for j in range(len(current_trains[l])):
                current_trains_life_slices[l][j] += 1
                new_loc = loops[l][0] + find_closest_past_station(current_trains_life_slices[l][j],
                                                                  times_between_stations[loops[l][0]:loops[l][1]],
                                                                  seconds_per_slice)
                if current_trains_loc[l][j] == new_loc:
                    continue
                current_trains_loc[l][j] = new_loc
                passengers_boarded = min(capacity - current_trains[l][j][current_trains_loc[l][j]],
                                         np.sum(remaining[current_trains_loc[l][j], current_trains_loc[l][j] + 1:]))
                total_boarded[i // group_results_n_slices] += passengers_boarded
                if np.sum(remaining[current_trains_loc[l][j], current_trains_loc[l][j] + 1:]) != 0:
                    fraction_boarded = passengers_boarded / np.sum(
                        remaining[current_trains_loc[l][j], current_trains_loc[l][j] + 1:])
                else:
                    fraction_boarded = 0
                if current_trains_loc[l][j] > 0:
                    current_trains[l][j][current_trains_loc[l][j]] += current_trains[l][j][current_trains_loc[l][j] - 1]
                current_trains[l][j][current_trains_loc[l][j]] += passengers_boarded
                passengers_exited = np.round(
                    remaining[current_trains_loc[l][j], current_trains_loc[l][j] + 1:] * fraction_boarded)
                current_trains[l][j][current_trains_loc[l][j] + 1:] -= passengers_exited
                remaining[current_trains_loc[l][j], current_trains_loc[l][j] + 1:] = np.round(
                    remaining[current_trains_loc[l][j], current_trains_loc[l][j] + 1:] * (1 - fraction_boarded))
                if current_trains_loc[l][j] == loops[l][1]:
                    state[l][1] += 1
                    trains_ended += 1
            current_trains[l] = current_trains[l][trains_ended:]
            current_trains_loc[l] = current_trains_loc[l][trains_ended:]
            current_trains_life_slices[l] = current_trains_life_slices[l][trains_ended:]
            trains_ended = 0
            for j in range(len(current_trains_opposite[l])):
                current_trains_opposite_life_slices[l][j] += 1
                new_loc = loops[l][0] + find_closest_past_station(current_trains_opposite_life_slices[l][j],
                                                                  times_between_stations_opposite[
                                                                  loops[l][0]:loops[l][1]], seconds_per_slice,
                                                                  opposite=1)
                if current_trains_opposite_loc[l][j] == new_loc:
                    continue
                current_trains_opposite_loc[l][j] = new_loc
                passengers_boarded = min(capacity - current_trains_opposite[l][j][current_trains_opposite_loc[l][j]],
                                         np.sum(remaining[current_trains_opposite_loc[l][j],
                                                :current_trains_opposite_loc[l][j]]))
                total_boarded[i // group_results_n_slices] += passengers_boarded
                if np.sum(remaining[current_trains_opposite_loc[l][j], :current_trains_opposite_loc[l][j]]) > 0:
                    fraction_boarded = passengers_boarded / np.sum(
                        remaining[current_trains_opposite_loc[l][j], :current_trains_opposite_loc[l][j]])
                else:
                    fraction_boarded = 0
                if current_trains_opposite_loc[l][j] < demand_arr.shape[1] - 1:
                    current_trains_opposite[l][j][current_trains_opposite_loc[l][j]] += current_trains_opposite[l][j][
                        current_trains_opposite_loc[l][j] + 1]
                current_trains_opposite[l][j][current_trains_opposite_loc[l][j]] += passengers_boarded
                passengers_exited = np.round(
                    remaining[current_trains_opposite_loc[l][j], :current_trains_opposite_loc[l][j]] * fraction_boarded)
                current_trains_opposite[l][j][:current_trains_opposite_loc[l][j]] -= passengers_exited
                remaining[current_trains_opposite_loc[l][j], :current_trains_opposite_loc[l][j]] = np.round(
                    remaining[current_trains_opposite_loc[l][j], :current_trains_opposite_loc[l][j]] * (
                                1 - fraction_boarded))
                if current_trains_opposite_loc[l][j] == loops[l][0]:
                    state[l][0] += 1
                    trains_ended += 1
            current_trains_opposite[l] = current_trains_opposite[l][trains_ended:]
            current_trains_opposite_loc[l] = current_trains_opposite_loc[l][trains_ended:]
            current_trains_opposite_life_slices[l] = current_trains_opposite_life_slices[l][trains_ended:]
    overhead = total_new - total_boarded
    return (total_new, total_boarded, total_moving_trains, total_moving_trains_opposite, overhead)


def freq_from_samples(samples, window_size=30, seconds_per_sample=30, result_per_n_minutes=10,
                      group_results_n_slices=5):
    result = np.zeros(len(samples) // group_results_n_slices)
    for i in range(len(samples)):
        l_edge = max(0, i - window_size // 2)
        r_edge = min(len(samples), i + window_size // 2)
        total_mins = (r_edge - l_edge) * seconds_per_sample / 60
        result[i // group_results_n_slices] += (result_per_n_minutes * np.sum(
            samples[l_edge:r_edge]) / total_mins) / group_results_n_slices
    return result


def schedule_to_departures(schedule_array, t_unit):
    departures = []
    for i in range(len(schedule_array)):
        if schedule_array[i] == 1:
            departures.append(i * t_unit)
    return departures


def find_syntagma_arrivals(
        schedule_red_anthoupoli,
        schedule_red_elliniko,
        schedule_blue_dimotiko_theatre1,
        schedule_blue_doukissis_plakentias,
        schedule_blue_dimotiko_theatre2,
        schedule_blue_aerodromio,
        t_anthoupoli_syntagma=840,  # seconds
        t_elliniko_syntagma=1020,
        t_dimotiko_theatre_syntagma=1440,
        t_doukissis_plakentias_syntagma=1200,
        t_aerodromio_syntagma=2400
):
    arrivals_red = np.zeros(3600 * 24)
    arrivals_blue = np.zeros(3600 * 24)
    for i in range(len(schedule_red_anthoupoli)):
        if schedule_red_anthoupoli[i] + t_anthoupoli_syntagma < 3600 * 24:
            arrivals_red[schedule_red_anthoupoli[i] + t_anthoupoli_syntagma] += 1
    for i in range(len(schedule_red_elliniko)):
        if schedule_red_elliniko[i] + t_elliniko_syntagma < 3600 * 24:
            arrivals_red[schedule_red_elliniko[i] + t_elliniko_syntagma] += 1
    for i in range(len(schedule_blue_dimotiko_theatre1)):
        if schedule_blue_dimotiko_theatre1[i] + t_dimotiko_theatre_syntagma < 3600 * 24:
            arrivals_blue[schedule_blue_dimotiko_theatre1[i] + t_dimotiko_theatre_syntagma] += 1
    for i in range(len(schedule_blue_dimotiko_theatre2)):
        if schedule_blue_dimotiko_theatre2[i] + t_dimotiko_theatre_syntagma < 3600 * 24:
            arrivals_blue[schedule_blue_dimotiko_theatre2[i] + t_dimotiko_theatre_syntagma] += 1
    for i in range(len(schedule_blue_doukissis_plakentias)):
        if schedule_blue_doukissis_plakentias[i] + t_doukissis_plakentias_syntagma < 3600 * 24:
            arrivals_blue[schedule_blue_doukissis_plakentias[i] + t_doukissis_plakentias_syntagma] += 1
    for i in range(len(schedule_blue_aerodromio)):
        if schedule_blue_aerodromio[i] + t_aerodromio_syntagma < 3600 * 24:
            arrivals_blue[schedule_blue_aerodromio[i] + t_aerodromio_syntagma] += 1
    return arrivals_red, arrivals_blue


def run_optimization_pipeline(demand_npy, line_num, min_headway, max_wait_min, initial_state, max_at_ends, weight_wait,
                              weight_train, max_cap, phase_out_val, loops, time_limit=300, phase_out_seconds=3600):
    t_unit = min_headway // 2
    ready_demand = convert_demand_to_correct_time_slice(np.array(demand_npy), t_unit)
    by_line = split_table_by_line(ready_demand)
    line_demand = by_line[line_num - 1]
    num_line_stations = line_demand.shape[1]
    line_1_times = [240, 180, 120, 120, 120, 120, 120, 120, 120, 180, 120, 120, 120, 60, 180, 60, 120, 120, 180, 120,
                    180, 120, 120]
    line_2_times = [60, 60, 120, 120, 120, 60, 60, 120, 120, 120, 60, 120, 60, 120, 120, 120, 120, 120, 120]
    line_3_times = [120, 120, 120, 120, 120, 120, 120, 180, 180, 120, 120, 120, 60, 120, 120, 120, 120, 120, 120, 60,
                    120, 120, 360, 120, 360, 300]
    if line_num == 1:
        sample_times = line_1_times
    elif line_num == 2:
        sample_times = line_2_times
    elif line_num == 3:
        sample_times = line_3_times
    if len(sample_times) != num_line_stations - 1:
        print("Unexpected number of stations:", num_line_stations)
        sample_times = [120] * (num_line_stations - 1)
    max_wait_slices = [max_wait_min[i] * 60 // t_unit for i in range(len(max_wait_min))]
    results = schedule_with_loops(
        loops=loops,
        line=line_num,
        demand_arr=ready_demand,
        times_between_stations=sample_times,
        times_between_stations_opposite=sample_times,
        initial_state=initial_state,
        max_train_num_at_ends=max_at_ends,
        min_t_between_trains=min_headway,
        max_wait_unit_slices=max_wait_slices,
        min_rotation_time=min_headway,
        forbidden_slices_idx=[],
        forbidden_slices_opposite_idx=[],
        max_capacity=max_cap,
        a=weight_wait / 100.0,
        b=weight_train / 100.0,
        time_limit=time_limit,
        phase_out_seconds=phase_out_seconds
    )
    # Collect all loop schedules (not just loop 0)
    x_scheduled = [results[i][0] for i in range(len(loops))]
    x1_scheduled = [results[i][1] for i in range(len(loops))]
    # Use the line-specific demand for simulation, matching user's local usage:
    # demand_arr = split_table_by_line(inp_arr)[line-1]
    tot_new, tot_boarded, tot_trains, tot_trains_opposite, overhead = simulate_loops(
        loops, line_demand, x_scheduled, x1_scheduled, initial_state,
        min_headway, [], [], max_cap, sample_times, sample_times
    )
    is_qualified = 1
    return x_scheduled, x1_scheduled, tot_new, tot_boarded, tot_trains, tot_trains_opposite, overhead, is_qualified
