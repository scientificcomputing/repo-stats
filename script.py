import condastats.cli
import pypistats
import pandas
import json
import subprocess
import sys
import warnings
import datetime
import math
owner = sys.argv[1]
repo = sys.argv[2]
conda_name = sys.argv[3]
pypi_name = sys.argv[4]

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


date_format = '%d-%m-%Y'
for key, infile in zip(["clones", "views"], [repo_clones, repo_views]):
    df = pandas.DataFrame.from_dict(infile[key])
    unique = infile["uniques"]

    dates = pandas.to_datetime(df["timestamp"])
    start_date = pandas.to_datetime(dates).sort_values().iloc[0]
    end_date = pandas.to_datetime(dates).sort_values().iloc[-1]
    print("-"*25)
    print(
        f"Github traffic review of https://www.github.com/{owner}/{repo} from {start_date.strftime(date_format)} to {end_date.strftime(date_format)}")
    print(f"Number of unique {key}: {unique}")
    num_days = (end_date-start_date).days

    if len(dates) != num_days+1:
        num_days = len(dates)
        warnings.warn("We do not have data for every day")
    print(
        f"Average unqiue vistors per day (can be duplicated over multiple days): {math.floor(df['uniques'].sum()/len(df['uniques']))}")

if conda_name != "None":
    stats = condastats.cli.overall(conda_name, monthly=True)[conda_name]
    conda_dates = pandas.Series(pandas.to_datetime(stats.index).sort_values())
    start_month = conda_dates.iloc[0]
    end_month = conda_dates.iloc[-1]
    month_format = "%m-%Y"
    print("-"*25)
    print(
        f"Monthly conda stats from {start_month.strftime(month_format)} to {end_month.strftime(month_format)}")
    print(f"Total downloads: {stats.sum()}")
    print(f"Average per month: {math.floor(stats.mean())}")


if pypi_name != "None":
    with_mirrors = True
    if with_mirrors:
        sub_key = "with_mirrors"
    else:
        sub_key = "without_mirrors"

    pypi_json = pypistats.overall(
        pypi_name, total="monthly", format="json")

    pypi_stats = json.loads(pypi_json)["data"]
    accumulate_stats = {"dates": [], "downloads": []}
    for month in pypi_stats:
        if month["category"] != sub_key:
            continue
        accumulate_stats["dates"].append(
            datetime.datetime.strptime(month["date"], "%Y-%m"))
        accumulate_stats["downloads"].append(month["downloads"])
    pypi_df = pandas.DataFrame.from_dict(accumulate_stats)
    start_date = pypi_df["dates"].sort_values().iloc[0]
    end_date = pypi_df["dates"].sort_values().iloc[-1]
    print("-"*25)
    print(
        f"PYPI: https://pypi.org/project/{pypi_name} ({sub_key}) from {start_date.strftime(date_format)} to {end_date.strftime(date_format)}")
    print(f"Total downloads: {pypi_df['downloads'].sum()}")
    print(
        f"Monthly average downloads: {math.floor(pypi_df['downloads'].mean())}")
