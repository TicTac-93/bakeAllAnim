# --------------------------------
#   Bake All Anim v1.0.0 Release
# --------------------------------

# Destroys instances of the dialog before recreating it
# This has to go first, before modules are reloaded or the ui var is re-declared.
try:
    ui.close()
except:
    pass

# --------------------
#       Modules
# --------------------

# PySide 2
from PySide2.QtUiTools import QUiLoader
import PySide2.QtWidgets as QtW
from PySide2.QtCore import QFile

# Import PyMXS, MaxPlus, and set up shorthand vars
import pymxs
import MaxPlus

# Misc
import time # Used for Debugging
import sys
import os

# --------------------
#      UI Class
# --------------------


class BakeAnimUI(QtW.QDialog):

    def __init__(self, ui_file, pymxs, parent=MaxPlus.GetQMaxMainWindow()):
        """
        The Initialization of the main UI class
        :param ui_file: The path to the .UI file from QDesigner
        :param runtime: The pymxs runtime
        :param parent: The main Max Window
        """
        # Init QtW.QDialog
        super(BakeAnimUI, self).__init__(parent)

        # ---------------------------------------------------
        #                    Variables
        # ---------------------------------------------------

        self._ui_file_string = ui_file
        self._pymxs = pymxs
        self._parent = parent

        # ---------------------------------------------------
        #                     Main Init
        # ---------------------------------------------------

        # UI Loader

        ui_file = QFile(self._ui_file_string)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self._widget = loader.load(ui_file)

        ui_file.close()

        # Attaches loaded UI to the dialog box

        main_layout = QtW.QVBoxLayout()
        main_layout.addWidget(self._widget)

        self.setLayout(main_layout)

        # Titling

        self._window_title = "Bake All Anim DEV BUILD"
        self.setWindowTitle(self._window_title)

        # ---------------------------------------------------
        #                   Widget Setup
        # ---------------------------------------------------

        # Frame Range
        self._spn_start = self.findChild(QtW.QSpinBox, 'spn_start')
        self._spn_end = self.findChild(QtW.QSpinBox, 'spn_end')
        self._spn_nth = self.findChild(QtW.QSpinBox, 'spn_nth')
        self._btn_range = self.findChild(QtW.QPushButton, 'btn_updateRange')
        self._chk_pad = self.findChild(QtW.QCheckBox, 'chk_pad')

        # Track Selection
        self._box_tracks = self.findChild(QtW.QWidget, 'box_tracks')
        self._btn_tracks = self.findChild(QtW.QPushButton, 'btn_updateTracks')
        self._chk_transforms = self.findChild(QtW.QCheckBox, 'chk_transforms')
        self._chk_modifiers = self.findChild(QtW.QCheckBox, 'chk_modifiers')
        self._chk_visibility = self.findChild(QtW.QCheckBox, 'chk_visibility')
        self._chk_materials = self.findChild(QtW.QCheckBox, 'chk_materials')

        # Bake
        self._btn_bake = self.findChild(QtW.QPushButton, 'btn_getBaked')
        self._bar_progress = self.findChild(QtW.QProgressBar, 'bar_progress')
        self._lbl_status = self.findChild(QtW.QLabel, 'lbl_status')

        # ---------------------------------------------------
        #                Function Connections
        # ---------------------------------------------------
        # This section is sparse because we don't worry about fetching and validating other settings until we bake.

        # Frame Range
        self._btn_range.pressed.connect(self._update_range)

        # Track Selection
        self._btn_tracks.pressed.connect(self._update_tracks)

        # Bake
        self._btn_bake.pressed.connect(self._bake)

        # ---------------------------------------------------
        #                  Parameter Setup
        # ---------------------------------------------------

        self._options = {'start': 0,
                         'end': 100,
                         'nth': 1,
                         'pad': False,
                         'transforms': True,
                         'modifiers': True,
                         'visibility': False,
                         'materials': False,
                         'tracks': []}

        # Label color vars
        self._err = "color=#e82309"
        self._wrn = "color=#f7bd0e"
        self._grn = "color=#3cc103"

        # ---------------------------------------------------
        #                   End of Init

    # ---------------------------------------------------
    #                  Private Methods
    # ---------------------------------------------------

    def _update_range(self):
        """
        Update the frame range spinners with the Max Time Slider range.
        """
        rt = self._pymxs.runtime
        self._spn_start.setValue(rt.animationRange.start)
        self._spn_end.setValue(rt.animationRange.end)

        # Update status label
        self._lbl_status.setText("<font %s>Updated:</font> Frame Range" % self._grn)

    def _get_settings(self, tracks=None, validate=None):
        """
        Get settings from UI and update self._options.  Optionally populate _options.tracks[] and validate settings.
        :param tracks: Bool, populate .tracks[] if True
        :param validate: Bool, validate settings if True
        :return: Bool indicating success or failure
        """
        # Update options from GUI
        self._options['start'] = self._spn_start.value()
        self._options['end'] = self._spn_end.value()
        self._options['nth'] = self._spn_nth.value()
        self._options['pad'] = self._chk_pad.isChecked()
        self._options['transforms'] = self._chk_transforms.isChecked()
        self._options['modifiers'] = self._chk_modifiers.isChecked()
        self._options['visibility'] = self._chk_visibility.isChecked()
        self._options['materials'] = self._chk_materials.isChecked()
        self._options['tracks'] = []

        # Pad frame range
        if self._options['pad'] and ((self._options['end'] - self._options['start']) % self._options['nth']) > 0:
            self._options['end'] += ((self._options['end'] - self._options['start']) % self._options['nth'])

        # Get selected tracks
        if tracks is True:
            layout = self._box_tracks.layout()
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget and widget.isChecked():
                    self._options['tracks'].append(str(widget.text()))

        # Validate options
        if validate is True:
            if self._options['start'] >= self._options['end']:
                self._lbl_status.setText("<font %s>ERROR:</font> Start frame is after End!" % self._err)
                return False

        return True

    def _update_tracks(self):
        """
        Updates the Track Selection box with a list of unique track names.
        """
        # DEBUG TIMER
        update_tracks_start = time.time()

        rt = self._pymxs.runtime
        layout = self._box_tracks.layout()
        selection = rt.getCurrentSelection()
        tracks = []
        self._get_settings()
        self._bar_progress.setMaximum(len(selection))
        self._lbl_status.setText("Finding animated tracks...")

        # Get track list from current selection
        for obj in selection:
            tracks = self._get_keyed_subtracks(obj, tracks, namesOnly=True)
            self._bar_progress.setValue(self._bar_progress.value()+1)

        # Update status label and progress bar
        self._lbl_status.setText("Updating Track Selection list...")
        self._bar_progress.setValue(0)
        self._bar_progress.setMaximum(len(tracks))

        # Clear the UI track list, repopulate with tracks we found
        for i in range(layout.count()):
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        index = 0
        if len(tracks) == 0:
            self._lbl_status.setText("<font %s>Warning:</font> No animated tracks found!" % self._wrn)
            self._bar_progress.setMaximum(1)
            self._bar_progress.setValue(1)

        else:
            for track in tracks:
                layout.addWidget(QtW.QCheckBox(track.split(' > ')[-1]))
                widget = layout.itemAt(index).widget()
                widget.setChecked(True)
                widget.setToolTip(track)
                self._bar_progress.setValue(self._bar_progress.value()+1)
                index += 1

            layout.addStretch()
        
            self._lbl_status.setText("<font %s>Found:</font> %d Tracks in %d Objects" % (self._grn,
                                                                                         len(tracks),
                                                                                         len(rt.getCurrentSelection())))

        # DEBUG TIMER
        update_tracks_end = time.time()
        print "Get Tracks took %sms" % round((update_tracks_end-update_tracks_start)*1000, 3)

    def _bake(self):
        """
        Update options, validate frame range, and bake selected tracks.
        """
        # DEBUG TIMER
        bake_start = time.time()
        
        rt = self._pymxs.runtime
        at = self._pymxs.attime
        animate = self._pymxs.animate

        if not self._get_settings(tracks=True, validate=True):
            return

        # Bake selected objects / tracks
        with self._pymxs.undo(True, 'Bake Selection'), self._pymxs.redraw(False):
            selection = rt.getCurrentSelection()

            # Update status label and progress bar
            self._lbl_status.setText("Baking %d Objects..." % len(selection))
            self._bar_progress.setValue(0)
            self._bar_progress.setMaximum(len(selection))

            for obj in selection:
                tracks = self._get_keyed_subtracks(obj, parent=obj.name)
                if len(tracks) == 0:
                    self._bar_progress.setValue(self._bar_progress.value()+1)
                    continue

                for track in tracks:

                    # Skip track if it's not selected
                    if track.name not in self._options['tracks']:
                        continue

                    # Cache track values at each frame, every n'th frame
                    anim = []
                    for t in range(self._options['start'], self._options['end']+1, self._options['nth']):
                        with at(t):
                            anim.append(track.value)

                    # Now clear the track and write cached keys
                    rt.deleteKeys(track)

                    anim_index = 0
                    with animate(True):
                        for t in range(self._options['start'], self._options['end']+1, self._options['nth']):
                            with at(t):
                                track.controller.value = anim[anim_index]
                            anim_index += 1

                self._bar_progress.setValue(self._bar_progress.value()+1)

        self._lbl_status.setText("<font %s>Baked:</font> %d tracks on %d objects" % (self._grn,
                                                                                     len(self._options['tracks']),
                                                                                     len(selection)))

        # DEBUG TIMER
        bake_end = time.time()
        # print "- Main Bake loop: %sms" % round((bake_end - bake_settings)*1000, 3)
        print "Bake took %sms" % round((bake_end - bake_start)*1000, 3)

    def _get_keyed_subtracks(self, track, parent=None, list=None, namesOnly=None, firstCall=None):
        # TODO: Test script with ALL 3dsMax Transform controllers, make sure ignore list isn't cutting anything out
        """
        Crawl through track heirarchy, building a list of animated tracks.  Exclude known top-level tracks that should
        not be baked.
        If run with namesOnly=True, the returned list is formatted like "parent > track", eg. "Path Constraint > Percent"
        :param track: The track to start crawling from - also used when called recursively
        :param list: The list of animated tracks, should start blank.
        :param namesOnly: If true, only consider the track names for uniqueness.
        :param parent: The name of the track from which this was called, used for namesOnly output.
        :param firstCall: Set internally, if unset we'll call ourself recursively in the chosen tracks.
        :return: A list of all (unique) animated track objects below the initial track.
        """
        # Default values
        if list is None:
            list = []
        if namesOnly is None:
            namesOnly = False
        if firstCall is None:
            firstCall = True
        if parent is None:
            long_name = track.name
        else:
            long_name = "%s > %s" % (parent, track.name)

        rt = self._pymxs.runtime
        ignore = ['Transform', 'Weights',
                  'Position XYZ', 'AudioPosition', 'Motion Clip SlavePos', 'Noise Position', 'Path Constraint', 'Position Expression', 'Position List', 'Position Motion Capture', 'Position Script', 'Ray To Surface Position', 'SlavePos', 'Spring', 'Surface',
                  'Euler XYZ', 'AudioRotation', 'LookAt Constraint', 'MCG LookAt', 'Motion Clip SlaveRotation', 'Noise Rotation', 'Ray To Surface Orientation', 'Rotation Motion Capture', 'Rotation Script', 'SlaveRotation',
                  'AudioScale', 'Motion Clip SlaveScale', 'Noise Scale', 'Scale Expression', 'Scale List', 'Scale Motion Capture', 'Scale Script', 'ScaleXYZ', 'SlaveScale']

        # DEBUG
        # track_properties = rt.getPropNames(track)
        # if track_properties is not None:
        #     print "Track: %s" % track.name
        #     print " -Parent: %s" % track.parent
        #     print " -Props: %s" % track_properties
        # /DEBUG

        # Call recursively on selected tracks
        if firstCall:
            # Track 1 is object visibility
            # Track 3 is object transforms
            # Track 4 is object modifiers
            # Track 5 is object material
            if self._options['visibility'] and rt.getSubAnim(track, 1) is not None:
                list = self._get_keyed_subtracks(rt.getSubAnim(track, 1), None, list, namesOnly, False)
            if self._options['transforms']:
                list = self._get_keyed_subtracks(rt.getSubAnim(track, 3), None, list, namesOnly, False)
            if self._options['modifiers']:
                list = self._get_keyed_subtracks(rt.getSubAnim(track, 4), None, list, namesOnly, False)
            if self._options['materials'] and rt.getSubAnim(track, 5) is not None:
                list = self._get_keyed_subtracks(rt.getSubAnim(track, 5), None, list, namesOnly, False)

        # Try to add current track to list, then continue calling self recursively
        else:
            if rt.isKindOf(track, rt.SubAnim) and rt.isController(track.controller) and track.isAnimated:
                if namesOnly:
                    if track.name not in ignore and long_name not in list:
                        list.append(long_name)
                elif track.name not in ignore and track not in list:
                    list.append(track)

            # Note: SubAnim list is 1-indexed.  Thanks, Autodesk.
            for i in range(1, track.numSubs + 1):
                list = self._get_keyed_subtracks(rt.getSubAnim(track, i), long_name, list, namesOnly, False)

        return list


# --------------------
#    Dialog Setup
# --------------------

# Path to UI file
_uif = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + "\\bakeAllAnim.ui"
_app = MaxPlus.GetQMaxMainWindow()
ui = BakeAnimUI(_uif, pymxs, _app)

# Punch it
ui.show()

# DEBUG
print "\rTest Version 60"
