from enum import Enum

DATASET_NAME_LIP = "LIP_Dataset"

class LIPLabels(Enum):
    Background      = 0
    Hat             = 1
    Hair            = 2
    Glove           = 3
    Sunglasses      = 4
    UpperClothes    = 5
    Dress           = 6
    Coat            = 7
    Socks           = 8
    Pants           = 9
    Jumpsuits       = 10
    Scarf           = 11
    Skirt           = 12
    Face            = 13
    Left_arm        = 14
    Right_arm       = 15
    Left_leg        = 16
    Right_leg       = 17
    Left_shoe       = 18
    Right_shoe      = 19

class ADE20K(Enum):
    wall_lbl = 0
    building_lbl = 1
    sky_lbl = 2
    floor_lbl = 3
    tree_lbl = 4
    ceiling_lbl = 5
    road_lbl = 6
    bed_lbl = 7
    windowpane_lbl = 8
    grass_lbl = 9
    cabinet_lbl = 10
    sidewalk_lbl = 11
    person_lbl = 12
    earth_lbl = 13
    door_lbl = 14
    table_lbl = 15
    mountain_lbl = 16
    plant_lbl = 17
    curtain_lbl = 18
    chair_lbl = 19
    car_lbl = 20
    water_lbl = 21
    painting_lbl = 22
    sofa_lbl = 23
    shelf_lbl = 24
    house_lbl = 25
    sea_lbl = 26
    mirror_lbl = 27
    rug_lbl = 28
    field_lbl = 29
    armchair_lbl = 30
    seat_lbl = 31
    fence_lbl = 32
    desk_lbl = 33
    rock_lbl = 34
    wardrobe_lbl = 35
    lamp_lbl = 36
    bathtub_lbl = 37
    railing_lbl = 38
    cushion_lbl = 39
    base_lbl = 40
    box_lbl = 41
    column_lbl = 42
    signboard_lbl = 43
    chest_of_drawers_lbl = 44
    counter_lbl = 45
    sand_lbl = 46
    sink_lbl = 47
    skyscraper_lbl = 48
    fireplace_lbl = 49
    refrigerator_lbl = 50
    grandstand_lbl = 51
    path_lbl = 52
    stairs_lbl = 53
    runway_lbl = 54
    case_lbl = 55
    pool_table_lbl = 56
    pillow_lbl = 57
    screen_door_lbl = 58
    stairway_lbl = 59
    river_lbl = 60
    bridge_lbl = 61
    bookcase_lbl = 62
    blind_lbl = 63
    coffee_table_lbl = 64
    toilet_lbl = 65
    flower_lbl = 66
    book_lbl = 67
    hill_lbl = 68
    bench_lbl = 69
    countertop_lbl = 70
    stove_lbl = 71
    palm_lbl = 72
    kitchen_island_lbl = 73
    computer_lbl = 74
    swivel_chair_lbl = 75
    boat_lbl = 76
    bar_lbl = 77
    arcade_machine_lbl = 78
    hovel_lbl = 79
    bus_lbl = 80
    towel_lbl = 81
    light_lbl = 82
    truck_lbl = 83
    tower_lbl = 84
    chandelier_lbl = 85
    awning_lbl = 86
    streetlight_lbl = 87
    booth_lbl = 88
    television_receiver_lbl = 89
    airplane_lbl = 90
    dirt_track_lbl = 91
    apparel_lbl = 92
    pole_lbl = 93
    land_lbl = 94
    bannister_lbl = 95
    escalator_lbl = 96
    ottoman_lbl = 97
    bottle_lbl = 98
    buffet_lbl = 99
    poster_lbl = 100
    stage_lbl = 101
    van_lbl = 102
    ship_lbl = 103
    fountain_lbl = 104
    conveyer_belt_lbl = 105
    canopy_lbl = 106
    washer_lbl = 107
    plaything_lbl = 108
    swimming_pool_lbl = 109
    stool_lbl = 110
    barrel_lbl = 111
    basket_lbl = 112
    waterfall_lbl = 113
    tent_lbl = 114
    bag_lbl = 115
    minibike_lbl = 116
    cradle_lbl = 117
    oven_lbl = 118
    ball_lbl = 119
    food_lbl = 120
    step_lbl = 121
    tank_lbl = 122
    trade_name_lbl = 123
    microwave_lbl = 124
    pot_lbl = 125
    animal_lbl = 126
    bicycle_lbl = 127
    lake_lbl = 128
    dishwasher_lbl = 129
    screen_lbl = 130
    blanket_lbl = 131
    sculpture_lbl = 132
    hood_lbl = 133
    sconce_lbl = 134
    vase_lbl = 135
    traffic_light_lbl = 136
    tray_lbl = 137
    ashcan_lbl = 138
    fan_lbl = 139
    pier_lbl = 140
    crt_screen_lbl = 141
    plate_lbl = 142
    monitor_lbl = 143
    bulletin_board_lbl = 144
    shower_lbl = 145
    radiator_lbl = 146
    glass_lbl = 147
    clock_lbl = 148
    flag_lbl = 149
