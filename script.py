import pandas
import json
import subprocess
import sys
import warnings
import math
owner = sys.argv[1]
repo = sys.argv[2]
clones = subprocess.run([
    'gh', 'api', "-H", "Accept:application/vnd.github+json",   "-H", "X-GitHub-Api-Version:2022-11-28",
    f'/repos/{owner}/{repo}/traffic/clones'], capture_output=True
)
views = subprocess.run([
    'gh', 'api', "-H", "Accept:application/vnd.github+json",   "-H", "X-GitHub-Api-Version:2022-11-28",
    f'/repos/{owner}/{repo}/traffic/views'], capture_output=True
)

repo_clones = json.loads(clones.stdout)
repo_views = json.loads(views.stdout)


view_df = pandas.DataFrame.from_dict(repo_views["views"])

date_format = '%d-%m-%Y'
for key, infile in zip(["clones", "views"], [repo_clones, repo_views]):
    df = pandas.DataFrame.from_dict(infile[key])
    unique = infile["uniques"]
    num_view_days = len(view_df)

    dates = pandas.to_datetime(df["timestamp"])
    start_date = pandas.to_datetime(dates).sort_values().iloc[0]
    end_date = pandas.to_datetime(dates).sort_values().iloc[-1]
    print("-"*25)
    print(
        f"Github traffic review from {start_date.strftime(date_format)} to {end_date.strftime(date_format)}")
    print(f"Number of unique {key}: {unique}")
    num_days = (end_date-start_date).days

    if len(dates) != num_days+1:
        num_days = len(dates)
        warnings.warn("We do not have data for every day")
    print(
        f"Average unqiue vistors per day (can be duplicated over multiple days): {math.floor(df['uniques'].sum()/len(df['uniques']))}")
