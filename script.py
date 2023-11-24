import argparse
import datetime
import json
import math
import subprocess
import warnings
from pathlib import Path
from typing import Sequence

import condastats.cli
import pandas
import pypistats
from launchpadlib.launchpad import Launchpad

_date_format = "%d-%m-%Y"


def get_conda_stats(name: str) -> None:
    stats = condastats.cli.overall(name, monthly=True)[name]
    conda_dates = pandas.Series(pandas.to_datetime(stats.index).sort_values())
    start_month = conda_dates.iloc[0]
    end_month = conda_dates.iloc[-1]
    month_format = "%m-%Y"
    end_month_str = end_month.strftime(month_format)
    print(
        f"Monthly conda stats from {start_month.strftime(month_format)} to {end_month_str}"
    )
    print(f"Total downloads: {stats.sum()}")
    print(f"Average per month: {math.floor(stats.mean())}")
    print(
        f"Num downloads last month({end_month_str}): {stats[end_month.strftime('%Y-%m')]}")


def get_github_stats(repository: str) -> None:
    clones = subprocess.run(
        [
            "gh",
            "api",
            "-H",
            "Accept:application/vnd.github+json",
            "-H",
            "X-GitHub-Api-Version:2022-11-28",
            f"/repos/{repository}/traffic/clones",
        ],
        capture_output=True,
    )
    views = subprocess.run(
        [
            "gh",
            "api",
            "-H",
            "Accept:application/vnd.github+json",
            "-H",
            "X-GitHub-Api-Version:2022-11-28",
            f"/repos/{repository}/traffic/views",
        ],
        capture_output=True,
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
            f"Github traffic review of https://www.github.com/{repository} from {start_date.strftime(_date_format)} to {end_date.strftime(_date_format)}"
        )
        print(f"Number of unique {key}: {unique}")
        num_days = (end_date - start_date).days

        if len(dates) != num_days + 1:
            num_days = len(dates)
            warnings.warn("We do not have data for every day")
        print(
            f"Average unqiue vistors per day (can be duplicated over multiple days): {math.floor(df['uniques'].sum()/len(df['uniques']))}"
        )


def get_pypi_stats(name: str, with_mirrors: bool) -> None:
    if with_mirrors:
        sub_key = "with_mirrors"
    else:
        sub_key = "without_mirrors"

    pypi_json = pypistats.overall(name, total="monthly", format="json")
    pypi_stats = json.loads(pypi_json)["data"]
    accumulate_stats = {"dates": [], "downloads": []}
    for month in pypi_stats:
        if month["category"] != sub_key:
            continue
        accumulate_stats["dates"].append(
            datetime.datetime.strptime(month["date"], "%Y-%m")
        )
        accumulate_stats["downloads"].append(month["downloads"])
    pypi_df = pandas.DataFrame.from_dict(accumulate_stats)
    start_date = pypi_df["dates"].sort_values().iloc[0]
    end_date = pypi_df["dates"].sort_values().iloc[-1]

    print(
        f"PYPI: https://pypi.org/project/{name} ({sub_key}) from {start_date.strftime(_date_format)} to {end_date.strftime(_date_format)}"
    )
    print(f"Total downloads: {pypi_df['downloads'].sum()}")
    print(
        f"Monthly average downloads: {math.floor(pypi_df['downloads'].mean())}")


def get_launchpad_info(
    user: str, name: str, package: str, start_date="2023-10-01", end_date="2023-10-31"
):
    cache_dir = (Path.cwd() / "cache").absolute
    launchpad = Launchpad.login_anonymously("just testing", "production")
    ppa = launchpad.people[user].getPPAByName(name=name)
    bins = ppa.getPublishedBinaries(binary_name=package, exact_match=True)
    downloaded_builds = {}
    for bin in bins:
        bin_count = bin.getDailyDownloadTotals(
            start_date=start_date, end_date=end_date)
        if len(bin_count) > 0:
            for date, count in bin_count.items():
                key = bin.binary_package_version
                if key in downloaded_builds:
                    downloaded_builds[key] += count
                else:
                    downloaded_builds[key] = count
    data = [[key, value] for (key, value) in downloaded_builds.items()]
    lp_df = pandas.DataFrame.from_records(data, columns=["binary", "count"])
    diff_days = datetime.datetime.strptime(
        end_date, "%Y-%m-%d"
    ) - datetime.datetime.strptime(start_date, "%Y-%m-%d")
    print(f"Launchpad downloads of {package}")
    print(
        f"Period {start_date} to {end_date} ({diff_days.days+1} days): {lp_df['count'].sum()}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--github",
        type=str,
        dest="github",
        default=None,
        help="Github location, format 'user/repository'",
    )
    parser.add_argument(
        "--conda", type=str, dest="conda", default=None, help="Name of conda package"
    )
    parser.add_argument(
        "--pypi", type=str, dest="pypi", default=None, help="Name of pypi package"
    )
    parser.add_argument(
        "--without-mirrors",
        action="store_false",
        default=True,
        dest="with_mirrors",
        help="If getting pypi images, decide if you want to get info with or without mirrors",
    )
    parser.add_argument(
        "--launchpad-user",
        default=None,
        type=str,
        dest="lu",
        help="Team/User owning package on Launchpad",
    )
    parser.add_argument(
        "--launchpad-ppa", default=None, type=str, dest="lppa", help="PPA on Launchpad"
    )
    parser.add_argument(
        "--launchpad-package",
        default=None,
        type=str,
        dest="lpackage",
        help="Package on Launchpad",
    )
    parser.add_argument(
        "--launchpad-month",
        default="October 2023",
        dest="lmonth",
        type=str,
        help="Month and Year to get data from",
    )
    parser.add_argument(
        "--docker",
        default=None,
        dest="docker",
        type=str,
        help="Name of docker image",
    )

    args = parser.parse_args(argv)
    if args.github is not None:
        get_github_stats(args.github)
        print("-" * 25)

    if args.conda is not None:
        get_conda_stats(args.conda)
        print("-" * 25)

    if args.pypi is not None:
        get_pypi_stats(args.pypi, args.with_mirrors)
        print("-" * 25)

    if args.lu is not None and args.lppa is not None and args.lpackage is not None:
        start_date = datetime.datetime.strptime(args.lmonth, "%B %Y")
        end_date = start_date.replace(
            month=start_date.month + 1, day=1
        ) - datetime.timedelta(days=1)
        get_launchpad_info(
            args.lu,
            args.lppa,
            args.lpackage,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )
        print("-" * 25)
    if args.docker is not None:
        get_docker_stats(args.docker)
    return 0


def get_docker_stats(image: str):
    output = subprocess.run(["curl", "-s", f"https://hub.docker.com/v2/repositories/{image}"],
                            capture_output=True,
                            )
    docker_output = json.loads(output.stdout)
    start_date = datetime.datetime.strptime(
        docker_output["date_registered"], "%Y-%m-%dT%H:%M:%S.%fZ")
    uct_now = datetime.datetime.utcnow()
    diff = uct_now - start_date
    # Rough estimeate of number of months
    months = math.floor(diff.days / 365 * 12)
    num_downloads = docker_output["pull_count"]
    print(f"Docker {image}")
    print(
        f"Number of downloads since {start_date.strftime('%d-%m-%Y')} to {uct_now.strftime('%d-%m-%Y')}: {num_downloads}")
    print(f"Average per month {math.floor(num_downloads/ months)}")


if __name__ == "__main__":
    raise SystemExit(main())
