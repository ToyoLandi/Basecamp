#Temp Config while autoGen version is built

'''
READ-ME - How to use this file
# 1. Any changes below may require you to relaunch the "LogGuru" application or you could get a "not responding" window.
# 2. "\\" is read as "\" - Keep in mind when defining file and executeable paths or you will run into errors
# 3. If you need a laugh. Hell, we all do - https://xkcd.com/2259/
'''

# Enviromental variables
config_netShare = "\\\\dnvcorpvf2.corp.nai.org\\nfs_dnvspr"
config_localFolder = "C:\\Users\\cspears1\\Desktop\\CaseContent"
config_nspReportTool = "C:\\Program Files (x86)\\Nsp Report\\nsp_report.exe"
config_atdDecryptTool = "C:\\Program Files (x86)\\Nsp Report\\atd-decryptfile.exe"
config_7zip = "C:\\Program Files\\7-Zip\\7z.exe"

# Options
config_autoUpload = True #False
config_uds_shortPath = True
config_cleanupAge = 90 #Days

#Terminal Color Settings. HEX Values are expected.
config_termnialBackgroundColor = '#1c2933' #Slate Blue
config_termnialTextColor = '#90f7ff' #Light Blue
'''
    '#2E0854' #Indigo
    '#ffffff' #White
    '#000000' #Black
    '#FF69B4' #Pink
    '#ffd961' #Light Orange
    '#bfff70' #Light Green
'''
# User-Defined Parsing Rules
config_parsingRules = [
    {'type':"atd", 'mode':"line", 'path':"opt\\amas\\version.txt", 'exp':1},
    {'type':"ips", 'mode':"line", 'path':"logstat.mgmt.log", 'exp':10},
    {'type':"nsm", 'mode':"line", 'path':"config\\ems.properties", 'exp':4}
    ]

#Developer Tools - How to break your app in one easy step!
config_enableDevTools = True #True