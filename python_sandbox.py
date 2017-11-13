import glob
path = "\\\\130.60.131.134\\fiwi_datenbank\\SCR\\"
dirs = glob.glob(path + "*/")
to_do = []
for d in dirs:
    name = d.replace(path, "").replace("\\", "").split("_")
    a = int(name[1])
    b = int(name[2])
    if a != 1 or b != 1:
        old_name = str(name[0]) + "_1_1"
        new_name = name[0] + "_" + name[1] + "_" + name[2]
        # if int(name[0]) not in [1062,13,167,183]:
        to_do.append([d, new_name, old_name])

print len(d)

for d in to_do:
    print d