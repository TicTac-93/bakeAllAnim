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

        self._window_title = "Bake All Anim v01"
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
        _rt = self._pymxs.runtime
        self._spn_start.setValue(_rt.animationRange.start)
        self._spn_end.setValue(_rt.animationRange.end)

        # Update status label
        self._lbl_status.setText("<font %s>Updated:</font> Frame Range" % self._grn)


    def _update_tracks(self):
        """
        Updates the Track Selection box with a list of unique track names.
        """
        _rt = self._pymxs.runtime
        tracks = []
        layout = self._box_tracks.layout()

        selection = _rt.getCurrentSelection()
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
        for track in tracks:
            layout.addWidget(QtW.QCheckBox(track))
            widget = layout.itemAt(index).widget()
            widget.setChecked(True)
            self._bar_progress.setValue(self._bar_progress.value()+1)
            index += 1

        layout.addStretch()
        
        self._lbl_status.setText("<font %s>Found:</font> %d Tracks in %d Objects" % (self._grn,
                                                                                     len(tracks),
                                                                                     len(_rt.getCurrentSelection())))


    def _bake(self):
        """
        Update options, validate frame range, and bake selected tracks.
        """
        _rt = self._pymxs.runtime
        _at = self._pymxs.attime
        _animate = self._pymxs.animate

        # Update options from GUI
        self._options['start'] = self._spn_start.value()
        self._options['end'] = self._spn_end.value()
        self._options['nth'] = self._spn_nth.value()
        self._options['pad'] = self._chk_pad.isChecked()
        self._options['tracks'] = []
        # Get selected tracks
        layout = self._box_tracks.layout()
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and widget.isChecked():
                self._options['tracks'].append(str(widget.text()))

        # Validate options
        if self._options['start'] >= self._options['end']:
            self._lbl_status.setText("<font %s>ERROR:</font> Start frame is after End!" % self._err)
            return

        # Apply padding if needed
        if self._options['pad'] and ((self._options['end'] - self._options['start']) % self._options['nth']) > 0:
            self._options['end'] += ((self._options['end'] - self._options['start']) % self._options['nth'])

        # Bake selected objects / tracks
        with self._pymxs.undo(True, 'Bake Selection'):
            selection = _rt.getCurrentSelection()

            # Update status label and progress bar
            self._lbl_status.setText("Baking %d Objects..." % len(selection))
            self._bar_progress.setValue(0)
            self._bar_progress.setMaximum(len(selection))

            for obj in selection:
                tracks = self._get_keyed_subtracks(obj)
                if len(tracks) == 0:
                    self._bar_progress.setValue(self._bar_progress.value()+1)
                    continue

                for track in tracks:
                    # Skip track if it's not selected
                    if track.name not in self._options['tracks']:
                        continue

                    # Cache track values _at each frame, every n'th frame
                    anim = []
                    for t in range(self._options['start'], self._options['end']+1, self._options['nth']):
                        with _at(t):
                            anim.append(track.value)

                    # Now clear the track and write cached keys
                    _rt.deleteKeys(track)

                    anim_index = 0
                    with _animate(True):
                        for t in range(self._options['start'], self._options['end']+1, self._options['nth']):
                            with _at(t):
                                track.controller.value = anim[anim_index]
                            anim_index += 1

                self._bar_progress.setValue(self._bar_progress.value()+1)

        self._lbl_status.setText("<font %s>Baked:</font> %d tracks on %d objects" % (self._grn,
                                                                                     len(self._options['tracks']),
                                                                                     len(selection)))


    def _get_keyed_subtracks(self, track, list=[], namesOnly=False):
        """
        Crawl through track heirarchy, building a list of animated tracks.  Exclude Position and Rotation parent tracks.
        :param track: The track to start crawling from - also used when called recursively
        :param list: The list of animated tracks, should start blank.
        :param namesOnly: If true, only consider the track names for uniqueness.
        :return: A list of all (unique) animated track objects below the initial track.
        """
        _rt = self._pymxs.runtime
        ignore = ['Transform', 'Position', 'Rotation']

        # Only add this track to the list if it's a SubAnim, has a controller, and has been animated
        if _rt.iskindof(track, _rt.SubAnim) and _rt.iscontroller(track.controller) and track.isanimated:
            if not namesOnly and track not in list and track.name not in ignore:
                list.append(track)
            elif namesOnly and track.name not in list and track.name not in ignore:
                list.append(track.name)

        # Always call self recursively on all children of this track
        # Note: SubAnim list is 1-indexed.  Thanks, Autodesk.
        for i in range(1, track.numsubs + 1):
            list = self._get_keyed_subtracks(_rt.getSubAnim(track, i), list, namesOnly)

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
