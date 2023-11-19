import argparse
import datetime
import json
import math
import subprocess
import warnings

import condastats.cli
import pandas
import pypistats

_date_format = '%d-%m-%Y'


def get_conda_stats(name: str):
    stats = condastats.cli.overall(name, monthly=True)[name]
    conda_dates = pandas.Series(pandas.to_datetime(stats.index).sort_values())
    start_month = conda_dates.iloc[0]
    end_month = conda_dates.iloc[-1]
    month_format = "%m-%Y"
    print(
        f"Monthly conda stats from {start_month.strftime(month_format)} to {end_month.strftime(month_format)}")
    print(f"Total downloads: {stats.sum()}")
    print(f"Average per month: {math.floor(stats.mean())}")


def get_github_stats(repository: str):
    clones = subprocess.run([
        'gh', 'api', "-H", "Accept:application/vnd.github+json",   "-H", "X-GitHub-Api-Version:2022-11-28",
        f'/repos/{repository}/traffic/clones'], capture_output=True
    )
    views = subprocess.run([
        'gh', 'api', "-H", "Accept:application/vnd.github+json",   "-H", "X-GitHub-Api-Version:2022-11-28",
        f'/repos/{repository}/traffic/views'], capture_output=True
    )

    repo_clones = json.loads(clones.stdout)
    repo_views = json.loads(views.stdout)

    for key, infile in zip(["clones", "views"], [repo_clones, repo_views]):
        df = pandas.DataFrame.from_dict(infile[key])
        unique = infile["uniques"]

        dates = pandas.to_datetime(df["timestamp"])
        start_date = pandas.to_datetime(dates).sort_values().iloc[0]
        end_date = pandas.to_datetime(dates).sort_values().iloc[-1]
        print(
            f"Github traffic review of https://www.github.com/{repository} from {start_date.strftime(_date_format)} to {end_date.strftime(_date_format)}")
        print(f"Number of unique {key}: {unique}")
        num_days = (end_date-start_date).days

        if len(dates) != num_days+1:
            num_days = len(dates)
            warnings.warn("We do not have data for every day")
        print(
            f"Average unqiue vistors per day (can be duplicated over multiple days): {math.floor(df['uniques'].sum()/len(df['uniques']))}")


def get_pypi_stats(name: str):
    if args.with_mirrors:
        sub_key = "with_mirrors"
    else:
        sub_key = "without_mirrors"

    pypi_json = pypistats.overall(
        args.pypi, total="monthly", format="json")

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

    print(
        f"PYPI: https://pypi.org/project/{args.pypi} ({sub_key}) from {start_date.strftime(_date_format)} to {end_date.strftime(_date_format)}")
    print(f"Total downloads: {pypi_df['downloads'].sum()}")
    print(
        f"Monthly average downloads: {math.floor(pypi_df['downloads'].mean())}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--github", type=str,
                        dest="github", default=None,
                        help="Github location, format 'user/repository'")
    parser.add_argument("--conda", type=str,
                        dest="conda", default=None,
                        help="Name of conda package")
    parser.add_argument("--pypi", type=str,
                        dest="pypi", default=None,
                        help="Name of pypi package")
    parser.add_argument("--without-mirrors", action="store_false",
                        default=True, dest="with_mirrors",
                        help="If getting pypi images, decide if you want to get info with or without mirrors")
    args = parser.parse_args()
    if args.github is not None:
        get_github_stats(args.github)
        print("-"*25)

    if args.conda is not None:
        get_conda_stats(args.conda)
        print("-"*25)

    if args.pypi is not None:
        get_pypi_stats(args.pypi)
        print("-"*25)
