# imports - standard imports
import grp
import os
import pwd
import shutil
import sys

# imports - module imports
import bench
from bench.utils import (
	exec_cmd,
	get_process_manager,
	log,
	run_frappe_cmd,
	sudoers_file,
	which,
	is_valid_frappe_branch,
)
from bench.utils.bench import build_assets, clone_apps_from
from bench.utils.render import job


@job(title="Initializing Bench {path}", success="Bench {path} initialized")
def init(
	path,
	apps_path=None,
	no_procfile=False,
	no_backups=False,
	frappe_path=None,
	erpnext_path=None,
	print_designer_path=None,
	hrms_path=None,
	payments_path=None,
	webshop_path=None,
	builder_path=None,
	crm_path=None,
	drive_path=None,
	frappe_branch=None,
	erpnext_branch=None,
	print_designer_branch=None,
	hrms_branch=None,
	payments_branch=None,
	webshop_branch=None,
	builder_branch=None,
	crm_branch=None,
	drive_branch=None,
	verbose=False,
	clone_from=None,
	skip_redis_config_generation=False,
	clone_without_update=False,
	skip_assets=False,
	python="python3",
	install_app=None,
	dev=False,
	skip_frappe_clone=False,
	skip_erpnext_clone=False,
	skip_print_designer_clone=False,
	skip_hrms_clone=False,
	skip_payments_clone=False,
	skip_webshop_clone=False,
	skip_builder_clone=False,
	skip_crm_clone=False,
	skip_drive_clone=False,
):
	"""Initialize a new bench directory

	* create a bench directory in the given path
	* setup logging for the bench
	* setup env for the bench
	* setup config (dir/pids/redis/procfile) for the bench
	* setup patches.txt for bench
	* clone & install frappe
	        * install python & node dependencies
	        * build assets
	* setup backups crontab
	"""

	# Use print("\033c", end="") to clear entire screen after each step and re-render each list
	# another way => https://stackoverflow.com/a/44591228/10309266

	import bench.cli
	from bench.app import get_app, install_apps_from_path
	from bench.bench import Bench

	verbose = bench.cli.verbose or verbose

	bench = Bench(path)

	bench.setup.dirs()
	bench.setup.logging()
	bench.setup.env(python=python)
	config = {}
	if dev:
		config["developer_mode"] = 1
	bench.setup.config(
		redis=not skip_redis_config_generation,
		procfile=not no_procfile,
		additional_config=config,
	)
	bench.setup.patches()

	# local apps
	if clone_from:
		clone_apps_from(
			bench_path=path, clone_from=clone_from, update_app=not clone_without_update
		)

	# remote apps
	else:
		default_branch = "axeane_kompta"
		frappe_path = frappe_path or "https://github.com/azizios011/frappe-Compatible_windows.git"
		frappe_branch = frappe_branch or default_branch
		is_valid_frappe_branch(frappe_path=frappe_path, frappe_branch=frappe_branch)
		frappe_app_path = os.path.join(path, "apps", "frappe")
		if not (skip_frappe_clone and os.path.lexists(frappe_app_path)):
			get_app(
				frappe_path,
				branch=frappe_branch,
				bench_path=path,
				skip_assets=True,
				verbose=verbose,
				resolve_deps=False,
			)

		# fetch remote apps using config file - deprecate this!
		if apps_path:
			install_apps_from_path(apps_path, bench_path=path)

		# Each entry: app folder name -> (path_flag_value, branch_flag_value, default_url, skip_clone_flag)
		# path_flag_value is None only when the flag was never passed on the command line
		# (it's "" for a bare flag, or a real URL/path when one was given).
		app_specs = {
			"erpnext": (
				erpnext_path,
				erpnext_branch,
				"https://github.com/azizios011/erpnext-Compatible_windows.git",
				skip_erpnext_clone,
			),
			"print_designer": (
				print_designer_path,
				print_designer_branch,
				"https://github.com/azizios011/Print-Designer_Compatible_windows.git",
				skip_print_designer_clone,
			),
			"hrms": (
				hrms_path,
				hrms_branch,
				"https://github.com/azizios011/hrms_Compatible_windows.git",
				skip_hrms_clone,
			),
			"payments": (
				payments_path,
				payments_branch,
				"https://github.com/azizios011/payments-Compatible_windows.git",
				skip_payments_clone,
			),
			"webshop": (
				webshop_path,
				webshop_branch,
				"https://github.com/azizios011/webshop-Compatible_windows.git",
				skip_webshop_clone,
			),
			"builder": (
				builder_path,
				builder_branch,
				"https://github.com/azizios011/builder-Compatible_windows.git",
				skip_builder_clone,
			),
			"crm": (
				crm_path,
				crm_branch,
				"https://github.com/azizios011/crm-Compatible_windows.git",
				skip_crm_clone,
			),
			"drive": (
				drive_path,
				drive_branch,
				"https://github.com/azizios011/drive-Compatible_windows.git",
				skip_drive_clone,
			),
		}

		# If no app flag was passed at all, keep the old behaviour: install everything.
		# The moment at least one app flag is passed (bare or with a URL), only the
		# apps that were explicitly named get cloned.
		any_app_flag_passed = any(spec[0] is not None for spec in app_specs.values())

		for app_name, (app_path, app_branch, default_url, skip_clone) in app_specs.items():
			requested = app_path is not None
			if any_app_flag_passed and not requested:
				continue

			resolved_path = app_path or default_url
			resolved_branch = app_branch or default_branch
			app_dir = os.path.join(path, "apps", app_name)
			if not (skip_clone and os.path.lexists(app_dir)):
				get_app(
					resolved_path,
					branch=resolved_branch,
					bench_path=path,
					skip_assets=True,
					verbose=verbose,
					resolve_deps=False,
				)

	# getting app on bench init using --install-app
	if install_app:
		get_app(
			install_app,
			branch=frappe_branch,
			bench_path=path,
			skip_assets=True,
			verbose=verbose,
			resolve_deps=False,
		)

	if not skip_assets:
		build_assets(bench_path=path)

	if not no_backups:
		bench.setup.backups()


def setup_sudoers(user):
	from bench.config.lets_encrypt import get_certbot_path

	if not os.path.exists("/etc/sudoers.d"):
		os.makedirs("/etc/sudoers.d")

		set_permissions = not os.path.exists("/etc/sudoers")
		with open("/etc/sudoers", "a") as f:
			f.write("\n#includedir /etc/sudoers.d\n")

		if set_permissions:
			os.chmod("/etc/sudoers", 0o440)

	template = bench.config.env().get_template("frappe_sudoers")
	frappe_sudoers = template.render(
		**{
			"user": user,
			"service": which("service"),
			"systemctl": which("systemctl"),
			"nginx": which("nginx"),
			"certbot": get_certbot_path(),
		}
	)

	with open(sudoers_file, "w") as f:
		f.write(frappe_sudoers)

	os.chmod(sudoers_file, 0o440)
	log(f"Sudoers was set up for user {user}", level=1)


def start(no_dev=False, concurrency=None, procfile=None, no_prefix=False, procman=None):
	program = which(procman) if procman else get_process_manager()
	if not program:
		raise Exception("No process manager found")

	os.environ["PYTHONUNBUFFERED"] = "true"
	if not no_dev:
		os.environ["DEV_SERVER"] = "true"

	command = [program, "start"]
	if concurrency:
		command.extend(["-c", concurrency])

	if procfile:
		command.extend(["-f", procfile])

	if no_prefix:
		command.extend(["--no-prefix"])

	os.execv(program, command)


def migrate_site(site, bench_path="."):
	run_frappe_cmd("--site", site, "migrate", bench_path=bench_path)


def backup_site(site, bench_path="."):
	run_frappe_cmd("--site", site, "backup", bench_path=bench_path)


def backup_all_sites(bench_path="."):
	from bench.bench import Bench

	for site in Bench(bench_path).sites:
		backup_site(site, bench_path=bench_path)


def fix_prod_setup_perms(bench_path=".", frappe_user=None):
	from glob import glob
	from bench.bench import Bench

	frappe_user = frappe_user or Bench(bench_path).conf.get("frappe_user")

	if not frappe_user:
		print("frappe user not set")
		sys.exit(1)

	globs = ["logs/*", "config/*"]
	for glob_name in globs:
		for path in glob(glob_name):
			uid = pwd.getpwnam(frappe_user).pw_uid
			gid = grp.getgrnam(frappe_user).gr_gid
			os.chown(path, uid, gid)


def setup_fonts():
	fonts_path = os.path.join("/tmp", "fonts")

	if os.path.exists("/etc/fonts_backup"):
		return

	exec_cmd("git clone https://github.com/frappe/fonts.git", cwd="/tmp")
	os.rename("/etc/fonts", "/etc/fonts_backup")
	os.rename("/usr/share/fonts", "/usr/share/fonts_backup")
	os.rename(os.path.join(fonts_path, "etc_fonts"), "/etc/fonts")
	os.rename(os.path.join(fonts_path, "usr_share_fonts"), "/usr/share/fonts")
	shutil.rmtree(fonts_path)
	exec_cmd("fc-cache -fv")

def get_mariadb_pkgconfig_path() -> str:
	import subprocess
	return subprocess.check_output(["brew", "--prefix", "mariadb-connector-c"]).decode("utf-8").strip() + "/lib/pkgconfig"

def check_pkg_config():
	"""
	pkg-config is required for building some python packages like libmysqlclient
	"""
	if shutil.which("pkg-config") is None:
		raise Exception("pkg-config is not installed. Please install it before proceeding.\n"
		"You can refer to https://docs.frappe.io/framework/user/en/installation")
