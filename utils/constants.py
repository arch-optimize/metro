L1_STATIONS = [
    '[01011] ΠΕΙΡΑΙΑΣ','[01012] ΦΑΛΗΡΟ','[01013] ΜΟΣΧΑTΟ','[01014] KΑΛΛΙΘΕΑ',
    '[01015] TΑΥΡΟΣ','[01016] ΠΕTΡΑΛΩΝΑ','[01017] ΘΗΣΕΙΟ','[01018] ΜΟΝΑΣTΗΡΑKΙ',
    '[01019] ΟΜOΝΟΙΑ','[01020] ΒΙKTΩΡΙΑ','[01021] ΑTTΙKΗ','[01022] ΑΓΙΟΣ ΝΙKOΛΑΟΣ',
    '[01023] KΑTΩ ΠΑTΗΣΙΑ','[01024] ΑΓΙΟΣ ΕΛΕΥΘΕΡΙΟΣ','[01025] ΑΝΩ ΠΑTΗΣΙΑ',
    '[01026] ΠΕΡΙΣΣOΣ','[01027] ΠΕΥKΑKΙΑ','[01028] ΝΕΑ ΙΩΝΙΑ','[01029] ΗΡΑKΛΕΙΟ',
    '[01030] ΕΙΡΗΝΗ','[01074] ΝΕΡΑTΖΙΩTΙΣΣΑ','[01031] ΜΑΡΟΥΣΙ','[01032] KΑT',
    '[01033] KΗΦΙΣΙΑ'
]

L2_STATIONS = [
    '[01034] ΑΝΘΟΥΠΟΛΗ','[01035] ΠΕΡΙΣTΕΡΙ','[01036] ΑΓΙΟΣ ΑΝTΩΝΙΟΣ','[01037] ΣΕΠOΛΙΑ',
    '[01038] ΑTTΙKΗ','[01039] ΣTΑΘΜOΣ ΛΑΡΙΣΗΣ','[01040] ΜΕTΑΞΟΥΡΓΕΙΟ','[01076] ΟΜOΝΟΙΑ',
    '[01041] ΠΑΝΕΠΙΣTΗΜΙΟ','[01042] ΣΥΝTΑΓΜΑ','[01043] ΑKΡOΠΟΛΗ','[01044] ΣΥΓΓΡΟΥ ΦΙΞ',
    '[01045] ΝΕΟΣ KOΣΜΟΣ','[01046] ΑΓΙΟΣ ΙΩΑΝΝΗΣ','[01047] ΔΑΦΝΗ','[01048] ΑΓΙΟΣ ΔΗΜΗTΡΙΟΣ',
    '[01049] ΗΛΙΟΥΠΟΛΗ','[01050] ΑΛΙΜΟΣ','[01051] ΑΡΓΥΡΟΥΠΟΛΗ','[01052] ΕΛΛΗΝΙKO'
]

L3_STATIONS = [
    '[01086] ΔΗΜΟΤΙΚΟ ΘΕΑΤΡΟ','[01085] ΠΕΙΡΑΙΑΣ','[01084] ΜΑΝΙΑΤΙΚΑ','[01083] ΝΙΚΑΙΑ',
    '[01082] ΚΟΡΥΔΑΛΛΟΣ','[01081] ΑΓΙΑ ΒΑΡΒΑΡΑ','[01053] ΑΓΙΑ ΜΑΡΙΝΑ','[01054] ΑΙΓΑΛΕΩ',
    '[01055] ΕΛΑΙΩΝΑΣ','[01056] KΕΡΑΜΕΙKOΣ','[01057] ΜΟΝΑΣTΗΡΑKΙ','[01059] ΕΥΑΓΓΕΛΙΣΜOΣ',
    '[01060] ΜΕΓΑΡΟ ΜΟΥΣΙKΗΣ','[01061] ΑΜΠΕΛOKΗΠΟΙ','[01062] ΠΑΝOΡΜΟΥ','[01063] KΑTΕΧΑKΗ',
    '[01064] ΕΘΝΙKΗ ΑΜΥΝΑ','[01065] ΧΟΛΑΡΓOΣ','[01066] ΝΟΜΙΣΜΑTΟKΟΠΕΙΟ',
    '[01067] ΑΓΙΑ ΠΑΡΑΣKΕΥΗ','[01068] ΧΑΛΑΝΔΡΙ','[01069] ΔΟΥKΙΣΣΗΣ ΠΛΑKΕΝTΙΑΣ',
    '[01080] ΠΑΛΛΗΝΗ','[01079] ΠΑΙΑΝΙΑ - KΑΝTΖΑ','[01078] KΟΡΩΠΙ','[01077] ΑΕΡΟΔΡΟΜΙΟ'
]

ALL_STATIONS = L1_STATIONS + L2_STATIONS + L3_STATIONS

DISC_PROFILES = [
    '[017] Ένοπλες Δυνάμεις','[004] Άτομα άνω των 65','[005] Βρέφη / Νήπια',
    '[001] Ενήλικες','[011] Μαθητές / Φοιτητές','[010] ΑΜΕΑ',
    '[014] Ελληνική Αστυνομία','[071] Ανώνυμο Προφίλ','[003] Νέοι',
    '[015] Πυροσβεστικό Σώμα','[002] Παιδιά','[021] Άνεργοι','[012] Μειωμένο'
]

DAY_OPTIONS = [
    {"label": "Monday", "value": "Monday"},
    {"label": "Tuesday", "value": "Tuesday"},
    {"label": "Wednesday", "value": "Wednesday"},
    {"label": "Thursday", "value": "Thursday"},
    {"label": "Friday", "value": "Friday"},
    {"label": "Saturday", "value": "Saturday"},
    {"label": "Sunday", "value": "Sunday"},
]

GRAPH_OPTIONS = [
    {"label": "Average weekday demand", "value": "avg_weekday_demand"},
    {"label": "Minimum weekday demand", "value": "min_weekday_demand"},
    {"label": "Maximum weekday demand", "value": "max_weekday_demand"},
    {"label": "Weekday comparison", "value": "weekday_comparison"},
    {"label": "Hourly OD profile", "value": "hourly_od_profile"},
    {"label": "Daily profile", "value": "daily_profile"},
    {"label": "Origin-Destination heatmap", "value": "od_heatmap"},
    {"label": "Boardings per station", "value": "boardings_per_station"},
    {"label": "Alightings per station", "value": "alightings_per_station"},
    {"label": "Station total activity", "value": "station_total_activity"},
    {"label": "Discount entries", "value": "discount_entries"},
    {"label": "Discount exits", "value": "discount_exits"},
    {"label": "Unmatched entries by hour", "value": "unmatched_entries_by_hour"},
    {"label": "Unmatched exits by hour", "value": "unmatched_exits_by_hour"},
    {"label": "Duplicates by station", "value": "duplicates_by_station"},
    {"label": "Almost duplicates by station", "value": "almost_duplicates_by_station"},
    {"label": "Same-station tracks", "value": "same_station_tracks"},
    {"label": "Data quality metrics", "value": "data_quality_metrics"},
    {"label": "First week comparison", "value": "first_week_comparison"},
    {"label": "Last week comparison", "value": "last_week_comparison"},
    {"label": "Holy week comparison", "value": "holy_week_comparison"},
    {"label": "Post-Easter week comparison", "value": "post_easter_week_comparison"},
    {"label": "Clean Monday comparison", "value": "clean_monday_comparison"},
    {"label": "Other holiday comparison", "value": "other_holiday_comparison"},
    {"label": "Average protest deviation", "value": "avg_protest_deviation"},
]

# Options for select_graph_to_display() in tab1 analytics
ANALYTICS_GRAPH_OPTIONS = [
    {"label": "Entire interval average", "value": "all_average"},
    {"label": "Entire interval minimum", "value": "all_min"},
    {"label": "Entire interval maximum", "value": "all_max"},
    {"label": "Month-day average", "value": "month_day_avg"},
    {"label": "Month-day minimum", "value": "month_day_min"},
    {"label": "Month-day maximum", "value": "month_day_max"},
    {"label": "Event deviation", "value": "event_deviation"},
    {"label": "First week (fw)", "value": "fw"},
    {"label": "Last week (lw)", "value": "lw"},
    {"label": "Holy week (mv)", "value": "mv"},
    {"label": "Easter week (vp)", "value": "vp"},
    {"label": "Clean Monday (kd)", "value": "kd"},
]

YEAR_OPTIONS = [{"label": str(y), "value": y} for y in [2023, 2024, 2025, 2026, 2027]]

SPECIAL_GRAPH_TYPES = {
    "first_week_comparison",
    "last_week_comparison",
    "holy_week_comparison",
    "post_easter_week_comparison",
    "clean_monday_comparison",
    "other_holiday_comparison",
    "avg_protest_deviation",
}

# Analytics graph types that return multiple series (list of arrays)
ANALYTICS_SPECIAL_GRAPH_TYPES = {"fw", "lw", "mv", "vp"}

FIRST_WEEK_BY_YEAR = {
    2023: ["2023-01-01","2023-01-02","2023-01-03","2023-01-04","2023-01-05","2023-01-06"],
    2024: ["2024-01-01","2024-01-02","2024-01-03","2024-01-04","2024-01-05","2024-01-06"],
    2025: ["2025-01-01","2025-01-02","2025-01-03","2025-01-04","2025-01-05","2025-01-06"],
}

LAST_WEEK_BY_YEAR = {
    2023: ["2023-12-24","2023-12-25","2023-12-26","2023-12-27","2023-12-28","2023-12-29","2023-12-30","2023-12-31"],
    2024: ["2024-12-24","2024-12-25","2024-12-26","2024-12-27","2024-12-28","2024-12-29","2024-12-30","2024-12-31"],
    2025: ["2025-12-24","2025-12-25","2025-12-26","2025-12-27","2025-12-28","2025-12-29","2025-12-30","2025-12-31"],
}

HOLY_WEEK_BY_YEAR = {
    2023: ["2023-04-10","2023-04-11","2023-04-12","2023-04-13","2023-04-14","2023-04-15","2023-04-16"],
    2024: ["2024-04-29","2024-04-30","2024-05-01","2024-05-02","2024-05-03","2024-05-04","2024-05-05"],
    2025: ["2025-04-14","2025-04-15","2025-04-16","2025-04-17","2025-04-18","2025-04-19","2025-04-20"],
}

POST_EASTER_WEEK_BY_YEAR = {
    2023: ["2023-04-17","2023-04-18","2023-04-19","2023-04-20","2023-04-21","2023-04-22","2023-04-23"],
    2024: ["2024-05-06","2024-05-07","2024-05-08","2024-05-09","2024-05-10","2024-05-11","2024-05-12"],
    2025: ["2025-04-21","2025-04-22","2025-04-23","2025-04-24","2025-04-25","2025-04-26","2025-04-27"],
}

CLEAN_MONDAY_BY_YEAR = {
    2023: "2023-02-27",
    2024: "2024-03-18",
    2025: "2025-03-03",
}

OTHER_HOLIDAYS_BY_YEAR = {
    2023: ["2023-03-25","2023-05-01","2023-08-15","2023-10-28","2023-11-17","2023-12-06"],
    2024: ["2024-03-25","2024-05-01","2024-08-15","2024-10-28","2024-11-17","2024-12-06"],
    2025: ["2025-03-25","2025-05-01","2025-08-15","2025-10-28","2025-11-17","2025-12-06"],
}

PROTESTS_BY_YEAR = {
    2023: ["2023-03-05","2023-03-08","2023-03-16"],
    2024: ["2024-02-08","2024-02-20","2024-02-22","2024-03-08"],
    2025: ["2025-02-07","2025-02-14"],
}

PROTEST_HOUR_BY_DATE = {
    "2023-03-05": 11,
    "2023-03-08": 12,
    "2023-03-16": 11,
    "2024-02-08": 11,
    "2024-02-20": 12,
    "2024-02-22": 12,
    "2024-03-08": 8,
    "2025-02-07": 12,
    "2025-02-14": 11,
}

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKENDS = {"Saturday", "Sunday"}


def special_dates_for_graph(graph_type: str, year: int) -> list[str]:
    if graph_type == "first_week_comparison":
        return FIRST_WEEK_BY_YEAR.get(year, [])
    if graph_type == "last_week_comparison":
        return LAST_WEEK_BY_YEAR.get(year, [])
    if graph_type == "holy_week_comparison":
        return HOLY_WEEK_BY_YEAR.get(year, [])
    if graph_type == "post_easter_week_comparison":
        return POST_EASTER_WEEK_BY_YEAR.get(year, [])
    if graph_type == "clean_monday_comparison":
        value = CLEAN_MONDAY_BY_YEAR.get(year)
        return [value] if value else []
    if graph_type == "other_holiday_comparison":
        return OTHER_HOLIDAYS_BY_YEAR.get(year, [])
    if graph_type == "avg_protest_deviation":
        return PROTESTS_BY_YEAR.get(year, [])
    return []