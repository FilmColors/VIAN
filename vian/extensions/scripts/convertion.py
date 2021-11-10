import os
import glob

for f in glob.glob("/Volumes/A32_4TB/fiwi_datenbank/MOV/to_convert/*"):
    input_file = f
    q = os.path.split(input_file)
    outp_file = os.path.join("/Volumes/A32_4TB/fiwi_datenbank/MOV/", q[1].split(".")[0] + ".mp4" )
    cmd = "ffmpeg -i "+input_file+" -c:v libx264 " + outp_file
    os.system(cmd)