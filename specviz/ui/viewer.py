from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ..third_party.qtpy.QtCore import *
from ..third_party.qtpy.QtWidgets import *
from ..third_party.qtpy.QtGui import *

from .qt.mainwindow import Ui_MainWindow
from .widgets.sub_windows import PlotSubWindow
from ..core.comms import Dispatch, DispatchHandle
from .widgets.menus import LayerContextMenu

from .widgets.windows import MainWindow
from ..plugins.data_list_plugin import DataListPlugin
from ..plugins.tool_tray_plugin import ToolTrayPlugin
from ..plugins.layer_list_plugin import LayerListPlugin
from ..plugins.statistics_plugin import StatisticsPlugin


class Viewer(object):
    """
    The `Viewer` is the main construction area for all GUI widgets. This
    object does **not** control the interactions between the widgets,
    but only their creation and placement.
    """
    def __init__(self):
        self.main_window = MainWindow()
        self.data_list_plugin = DataListPlugin(self.main_window)
        self.main_window.addDockWidget(Qt.LeftDockWidgetArea,
                                       self.data_list_plugin)

        self.layer_list_plugin = LayerListPlugin(self.main_window)
        self.main_window.addDockWidget(Qt.LeftDockWidgetArea,
                                       self.layer_list_plugin)

        self.tool_tray_plugin = ToolTrayPlugin(self.main_window)
        self.main_window.addDockWidget(Qt.RightDockWidgetArea,
                                       self.tool_tray_plugin)

        self.statistics_plugin = StatisticsPlugin(self.main_window)
        self.main_window.addDockWidget(Qt.LeftDockWidgetArea,
                                       self.statistics_plugin)

        self._setup_connections()

    def old__init__(self, parent=None):
        super(Viewer, self).__init__()
        self._current_sub_window = None

        self.main_window = Ui_MainWindow()
        self.main_window.setupUi(self)
        self.wgt_data_list = self.main_window.listWidget
        self.wgt_layer_list = self.main_window.treeWidget_2
        self.wgt_model_list = self.main_window.treeWidget
        self.wgt_model_list.setHeaderLabels(["Parameter", "Value"])

        # Setup
        self._setup_connections()

        # Context menus
        self.wgt_layer_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layer_context_menu = LayerContextMenu()

        self.wgt_model_list.setContextMenuPolicy(Qt.CustomContextMenu)

        # Setup event handler
        DispatchHandle.setup(self)

    def _setup_connections(self):
        # Listen for subwindow selection events, update layer list on selection
        self.main_window.mdi_area.subWindowActivated.connect(
            lambda wi: Dispatch.on_selected_window.emit(
            window=wi.widget() if wi is not None else None))

        # When a user edits the model parameter field, validate the input
        # self.wgt_model_list.itemChanged.connect(
        #         self._model_parameter_validation)

    @DispatchHandle.register_listener("on_selected_layer")
    def _set_model_tool_options(self, layer_item):
        if layer_item is None:
            self.main_window.createModelLayerButton.hide()
            self.main_window.updateModelLayerButton.hide()
            self.main_window.fittingRoutinesGroupBox.setEnabled(False)
            self.main_window.loadModelButton.setEnabled(False)
            self.main_window.saveModelButton.setEnabled(False)
            self.main_window.exportModelButton.setEnabled(False)

            return

        layer = layer_item.data(0, Qt.UserRole)

        if not hasattr(layer, 'model'):
            self.main_window.createModelLayerButton.show()
            self.main_window.updateModelLayerButton.hide()
            self.main_window.fittingRoutinesGroupBox.setEnabled(False)
            self.main_window.saveModelButton.setEnabled(False)
            self.main_window.exportModelButton.setEnabled(False)
            self.main_window.loadModelButton.setEnabled(True)
        else:
            self.main_window.createModelLayerButton.hide()
            self.main_window.updateModelLayerButton.show()
            self.main_window.fittingRoutinesGroupBox.setEnabled(True)
            self.main_window.saveModelButton.setEnabled(True)
            self.main_window.exportModelButton.setEnabled(True)
            self.main_window.loadModelButton.setEnabled(False)

    def _set_current_sub_window(self, sub_window):
        sub_window = sub_window or self.main_window.mdi_area.currentSubWindow()

        if sub_window is None:
            sub_window = self.main_window.mdi_area.activatePreviousSubWindow()

        if self._current_sub_window != sub_window:
            self._current_sub_window = sub_window
            Dispatch.on_selected_window.emit(window=self._current_sub_window)

    @property
    def current_model_item(self):
        return self.wgt_model_list.currentItem()

    @property
    def current_sub_window(self):
        """
        Returns the currently active `PlotSubWindow` object.

        Returns
        -------
        sub_window : PlotSubWindow
            The currently active `PlotSubWindow` object.
        """
        if self._current_sub_window is not None:
            return self._current_sub_window.widget()

    @property
    def current_model(self):
        return self.main_window.modelsComboBox.currentText()

    @property
    def current_fitter(self):
        return self.main_window.fittingRoutinesComboBox.currentText()

    @property
    def current_model_formula(self):
        return self.main_window.lineEdit.text()

    def open_file_dialog(self, filters):
        """
        Given a list of filters, prompts the user to select an existing file
        and returns the file path and filter.

        Parameters
        ----------
        filters : list
            List of filters for the dialog.

        Returns
        -------
        file_name : str
            Path to the selected file.
        selected_filter : str
            The chosen filter (this indicates which custom loader from the
            registry to use).
        """
        dialog = QFileDialog(self.main_window)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilters([x for x in filters])

        if dialog.exec_():
            file_names = dialog.selectedFiles()
            selected_filter = dialog.selectedNameFilter()

            return file_names[0], selected_filter

        return None, None

    @DispatchHandle.register_listener("on_added_model")
    def add_model_item(self, model, layer, unique=True):
        """
        Adds an `astropy.modeling.Model` to the loaded model tree widget.

        Parameters
        ----------
        """
        if model is None:
            return

        if unique:
            if self.get_model_item(model) is not None:
                return

        name = model.name

        if not name:
            count = 1

            root = self.wgt_model_list.invisibleRootItem()

            for i in range(root.childCount()):
                child = root.child(i)

                if isinstance(model, child.data(0, Qt.UserRole).__class__):
                    count += 1

            name = model.__class__.__name__.replace('1D', '') + str(count)
            model._name = name

        new_item = QTreeWidgetItem()
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)

        new_item.setText(0, name)
        new_item.setData(0, Qt.UserRole, model)

        for i, para in enumerate(model.param_names):
            new_para_item = QTreeWidgetItem(new_item)
            new_para_item.setText(0, para)
            new_para_item.setData(0, Qt.UserRole,
                                  model.parameters[i])
            new_para_item.setText(1, "{:4.4g}".format(model.parameters[i]))
            new_para_item.setFlags(new_para_item.flags() | Qt.ItemIsEditable)

        self.wgt_model_list.addTopLevelItem(new_item)

    @DispatchHandle.register_listener("on_removed_model")
    def remove_model_item(self, model=None, layer=None):
        root = self.wgt_model_list.invisibleRootItem()

        for i in range(root.childCount()):
            child = root.child(i)

            if child is None:
                continue

            if child.data(0, Qt.UserRole) == model:
                root.removeChild(child)
                break

    def update_model_item(self, model):
        if hasattr(model, '_submodels'):
            for sub_model in model._submodels:
                self.update_model_item(sub_model)
            else:
                return

        model_item = self.get_model_item(model)

        if model_item is None:
            return

        for i, para in enumerate(model.param_names):
            for i in range(model_item.childCount()):
                param_item = model_item.child(i)

                if param_item.text(0) == para:
                    param_item.setText(1, "{:4.4g}".format(
                        model.parameters[i]))

    def get_model_item(self, model):
        root = self.wgt_model_list.invisibleRootItem()

        for i in range(root.childCount()):
            child = root.child(i)

            if child.data(0, Qt.UserRole) == model:
                return child

    def _model_parameter_validation(self, item, col):
        if col == 0:
            return

        try:
            txt = "{:4.4g}".format(float(item.text(col)))
            item.setText(col, txt)
            item.setData(col, Qt.UserRole, float(item.text(col)))
        except ValueError:
            prev_val = item.data(col, Qt.UserRole)
            item.setText(col, str(prev_val))

    def get_model_inputs(self):
        """
        Returns the model and current parameters displayed in the UI.

        Returns
        -------
        models : dict
            A dictionary with the model instance as the key and a list of
            floats as the parameters values.
        """
        root = self.wgt_model_list.invisibleRootItem()
        models = {}

        for model_item in [root.child(j) for j in range(root.childCount())]:
            model = model_item.data(0, Qt.UserRole)
            args = []

            for i in range(model_item.childCount()):
                child_item = model_item.child(i)
                child = child_item.text(1)

                args.append(float(child))

            models[model] = args

        return models

    def clear_layer_widget(self):
        self.wgt_layer_list.clear()

    def clear_model_widget(self):
        self.wgt_model_list.clear()

    @DispatchHandle.register_listener("on_updated_stats")
    def update_statistics(self, stats, layer):
        self.main_window.currentLayerLineEdit.setText("{}".format(layer.name))

        if 'mean' in stats:
            self.main_window.meanLineEdit.setText("{0:4.4g}".format(
                stats['mean'].value))

            self.main_window.medianLineEdit.setText("{0:4.4g}".format(
                stats['median'].value))

            self.main_window.standardDeviationLineEdit.setText("{0:4.4g}".format(
                stats['stddev'].value))

            self.main_window.totalLineEdit.setText("{0:4.4g}".format(
                float(stats['total'].value)))

            self.main_window.dataPointCountLineEdit.setText(
                str(stats['npoints']))

        if 'eq_width' in stats:
            self.main_window.equivalentWidthLineEdit.setText("{0:4.4g}".format(
                float(stats['eq_width'].value)))

        if 'centroid' in stats:
            self.main_window.centroidLineEdit.setText("{0:5.5g}".format(
                float(stats['centroid'].value)))

        if 'flux' in stats:
            self.main_window.fluxLineEdit.setText("{0:4.4g}".format(
                float(stats['flux'].value)))

        if 'avg_cont' in stats:
            self.main_window.meanContinuumLineEdit.setText("{0:4.4g}".format(
                float(stats['avg_cont'].value)))
