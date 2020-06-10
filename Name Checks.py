import os


cwd = os.getcwd()
batter_files = open(os.path.join(cwd, "Similarity Scores", "2019 Batter Similarity Scores.csv"))
cmp_file = open("Master Roster.csv")
names = batter_files.readlines()[0].split(",")[1:]
cmp_names = []
for line in cmp_file.readlines()[1:]:
    name = line.split(",")[0]
    cmp_names.append(name)

for name in names:
    if name.strip() not in cmp_names:
        print(name)

pitcher_file = open(os.path.join(cwd, "Similarity Scores", "2019 Pitcher Similarity Scores.csv"))
names = pitcher_file.readlines()[0].split(",")[1:]
for file in os.listdir(os.path.join(cwd, "Bullpens")):
    if file.endswith("Bullpen.csv") and file.startswith("2018"):
        with open(os.path.join(cwd, "Bullpens", file)) as open_file:
            for i, line in enumerate(open_file.readlines()):
                if i % 8 == 0:
                    name = line.split(",")[0]
                    if name.strip() != "Composite" and name.strip() not in names:
                        print(file)
                        print(name.strip())
