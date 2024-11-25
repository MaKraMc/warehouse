from gi.repository import Gio, Gtk, GLib, Gdk, Flatpak
from .error_toast import ErrorToast
import subprocess, os, pathlib

home = f"{pathlib.Path.home()}"
icon_theme = Gtk.IconTheme.new()
icon_theme.add_search_path(f"{home}/.local/share/flatpak/exports/share/icons")
direction = Gtk.Image().get_direction()

class HostInfo:
	home = home
	clipboard = Gdk.Display.get_default().get_clipboard()
	main_window = None
	snapshots_path = f"{home}/.var/app/io.github.flattool.Warehouse/data/Snapshots/"

	# Get all possible installation icon theme dirs
	output = subprocess.run(
		["flatpak-spawn", "--host", "flatpak", "--installations"],
		text=True,
		capture_output=True,
	).stdout
	lines = output.strip().split("\n")
	for i in lines:
		icon_theme.add_search_path(f"{i}/exports/share/icons")

	installations = []
	n_remotes = []
	packages = []

	masks = {}
	pins = {}
	dependent_runtime_refs = []

	# stuff for compat while working
	flatpaks = []
	id_to_flatpak = {}
	ref_to_flatpak = {}
	remotes = {}

	@classmethod
	def get_flatpaks(this, callback=None):
		# Callback is a function to run after the host flatpaks are found
		this.flatpaks.clear()
		this.id_to_flatpak.clear()
		this.ref_to_flatpak.clear()
		this.n_remotes.clear()
		this.installations.clear()
		this.masks.clear()
		this.pins.clear()
		this.dependent_runtime_refs.clear()

		def thread(task, *args):
			user_installation_path = f"{GLib.get_user_data_dir()}/flatpak"
			user_installation_file = Gio.File.new_for_path(user_installation_path)
			user_installation = Flatpak.Installation.new_for_path(user_installation_file, True)

			this.installations.append(user_installation)
			this.installations += Flatpak.get_system_installations()

			for installation in this.installations:
				installation.cached_remotes = installation.list_remotes()
				installation.cached_packages = installation.list_installed_refs()
				this.n_remotes += installation.cached_remotes
				this.packages += installation.cached_packages

				for package in installation.cached_packages:
					package.installation = installation
					# package.dependent_runtime = this.get_dependant_runtime(package)
					#  This should instead be ran when the user clicks an app row in the package list,
					#  as it is slow to do for all of them at once, so only do it on the package to show info of

		Gio.Task.new(None, None, callback).run_in_thread(thread)

	@classmethod
	def get_dependant_runtime(this, package):
		installation = package.installation.get_id()
		cmd_installation = ""
		match installation:
			case 'user': cmd_installation = '--user'
			case 'default': cmd_installation = '--system'
			case _: cmd_installation = f'--installation={installation}'

		cmd = ['flatpak-spawn', '--host', 'flatpak', 'info', '--show-runtime', cmd_installation, package.format_ref()]
		output = subprocess.run(cmd, text=True, capture_output=True, check=True).stdout.strip()
		if output == "-":
			return None
		else:
			for package in package.installation.cached_packages:
				if package.format_ref() == f'runtime/{output}':
					return package
			else:
				return None
