import csv

def get_country_codes():
    with open("data/country_codes.csv", "r") as f:
        reader = csv.reader(f)
        d = dict()
        for i, r in enumerate(reader):
            d[r[0]] = r

    return d

def get_color_processes():
    """
    :return: Returns all Color Processes from the color_processes.txt as list
    """
    p = []
    with open("data/color_processes.txt", "r") as f:
        for t in f:
            p.append(t.replace("\n", "").strip())
    return p

filmography_meta = dict(
    country_codes = get_country_codes(),
    color_processes = get_color_processes()
)

print(filmography_meta)