import logging
import time
import uuid

from PySide2 import QtCore, QtGui

from PySide2.QtWidgets import QMessageBox, QApplication, QTableView

from sportorg import config
from sportorg.common.otime import OTime
from sportorg.gui.dialogs.about import AboutDialog
from sportorg.gui.dialogs.cp_delete import CPDeleteDialog
from sportorg.gui.dialogs.entry_filter import DialogFilter
from sportorg.gui.dialogs.entry_mass_edit import MassEditDialog
from sportorg.gui.dialogs.event_properties import EventPropertiesDialog
from sportorg.gui.dialogs.file_dialog import get_open_file_name, get_save_file_name
from sportorg.gui.dialogs.live_dialog import LiveDialog
from sportorg.gui.dialogs.not_start_dialog import NotStartDialog
from sportorg.gui.dialogs.number_change import NumberChangeDialog
from sportorg.gui.dialogs.print_properties import PrintPropertiesDialog
from sportorg.gui.dialogs.relay_clone_dialog import RelayCloneDialog
from sportorg.gui.dialogs.relay_number_dialog import RelayNumberDialog
from sportorg.gui.dialogs.rent_cards_dialog import RentCardsDialog
from sportorg.gui.dialogs.report_dialog import ReportDialog
from sportorg.gui.dialogs.search_dialog import SearchDialog
from sportorg.gui.dialogs.settings import SettingsDialog
from sportorg.gui.dialogs.sportorg_import_dialog import SportOrgImportDialog
from sportorg.gui.dialogs.start_handicap_dialog import StartHandicapDialog
from sportorg.gui.dialogs.start_preparation import StartPreparationDialog, guess_courses_for_groups
from sportorg.gui.dialogs.start_time_change_dialog import StartTimeChangeDialog
from sportorg.gui.dialogs.teamwork_properties import TeamworkPropertiesDialog
from sportorg.gui.dialogs.telegram_dialog import TelegramDialog
from sportorg.gui.dialogs.text_io import TextExchangeDialog
from sportorg.gui.dialogs.timekeeping_properties import TimekeepingPropertiesDialog
from sportorg.gui.menu.action import Action
from sportorg.gui.utils.custom_controls import messageBoxQuestion
from sportorg.libs.winorient.wdb import write_wdb
from sportorg.models.memory import race, ResultStatus, ResultManual, find
from sportorg.models.result.result_calculation import ResultCalculation
from sportorg.models.result.result_checker import ResultChecker
from sportorg.models.start.start_preparation import guess_corridors_for_groups, copy_bib_to_card_number, copy_card_number_to_bib
from sportorg.modules import testing
from sportorg.modules.backup.json import get_races_from_file
from sportorg.modules.iof import iof_xml
from sportorg.modules.ocad import ocad
from sportorg.modules.ocad.ocad import OcadImportException
from sportorg.modules.sfr.sfrreader import SFRReaderClient
from sportorg.modules.sportident.sireader import SIReaderClient
from sportorg.modules.sportiduino.sportiduino import SportiduinoClient
from sportorg.modules.teamwork import Teamwork
from sportorg.modules.telegram.telegram import TelegramClient
from sportorg.modules.updater import checker
from sportorg.modules.winorient import winorient
from sportorg.modules.winorient.wdb import WDBImportError, WinOrientBinary
from sportorg.language import _


class NewAction(Action):
    def execute(self):
        self.app.create_file()


class SaveAction(Action):
    def execute(self):
        self.app.save_file()


class OpenAction(Action):
    def execute(self):
        file_name = get_open_file_name(_('Open SportOrg file'), _("SportOrg file (*.json)"))
        self.app.open_file(file_name)


class SaveAsAction(Action):
    def execute(self):
        self.app.save_file_as()


class OpenRecentAction(Action):
    def execute(self):
        pass


class CopyAction(Action):
    def execute(self):
        if self.app.current_tab not in range(5):
            return
        table = self.app.get_current_table()
        sel_model = table.selectionModel()
        data = '\t'.join(sel_model.model().get_headers()) + '\n'
        indexes = sel_model.selectedRows()
        for index in indexes:
            row = [str(row) for row in sel_model.model().get_data(index.row())]
            data += '\t'.join(row) + '\n'
        QtGui.qApp.clipboard().setText(data)


class DuplicateAction(Action):
    def execute(self):
        if self.app.current_tab not in range(5):
            return
        table = self.app.get_current_table()
        sel_model = table.selectionModel()
        indexes = sel_model.selectedRows()
        if len(indexes):
            sel_model.model().duplicate(indexes[0].row())
            self.app.refresh()


class SettingsAction(Action):
    def execute(self):
        SettingsDialog().exec_()


class EventSettingsAction(Action):
    def execute(self):
        EventPropertiesDialog().exec_()


class CSVWinorientImportAction(Action):
    def execute(self):
        file_name = get_open_file_name(_('Open CSV Winorient file'), _("CSV Winorient (*.csv)"))
        if file_name is not '':
            try:
                winorient.import_csv(file_name)
            except Exception as e:
                logging.error(str(e))
                QMessageBox.warning(self.app, _('Error'), _('Import error') + ': ' + file_name)
            self.app.init_model()


class WDBWinorientImportAction(Action):
    def execute(self):
        file_name = get_open_file_name(_('Open WDB Winorient file'), _("WDB Winorient (*.wdb)"))
        if file_name is not '':
            try:
                winorient.import_wo_wdb(file_name)
            except WDBImportError as e:
                logging.error(str(e))
                logging.exception(e)
                QMessageBox.warning(self.app, _('Error'), _('Import error') + ': ' + file_name)
            self.app.init_model()


class OcadTXTv8ImportAction(Action):
    def execute(self):
        file_name = get_open_file_name(_('Open Ocad txt v8 file'), _("Ocad classes v8 (*.txt)"))
        if file_name is not '':
            try:
                ocad.import_txt_v8(file_name)
            except OcadImportException as e:
                logging.error(str(e))
                QMessageBox.warning(self.app, _('Error'), _('Import error') + ': ' + file_name)
            self.app.init_model()


class WDBWinorientExportAction(Action):
    def execute(self):
        file_name = get_save_file_name(_('Save As WDB file'), _("WDB file (*.wdb)"),
                                       '{}_sportorg_export'.format(race().data.get_start_datetime().strftime("%Y%m%d")))
        if file_name is not '':
            try:
                wb = WinOrientBinary()

                self.app.clear_filters(False)
                wdb_object = wb.export()
                self.app.apply_filters()

                write_wdb(wdb_object, file_name)
            except Exception as e:
                logging.exception(str(e))
                QMessageBox.warning(self.app, _('Error'), _('Export error') + ': ' + file_name)


class IOFResultListExportAction(Action):
    def execute(self):
        file_name = get_save_file_name(_('Save As IOF xml'), _('IOF xml (*.xml)'),
                                       '{}_resultList'.format(race().data.get_start_datetime().strftime("%Y%m%d")))
        if file_name is not '':
            try:
                iof_xml.export_result_list(file_name)
            except Exception as e:
                logging.error(str(e))
                QMessageBox.warning(self.app, _('Error'), _('Export error') + ': ' + file_name)


class IOFEntryListImportAction(Action):
    def execute(self):
        file_name = get_open_file_name(_('Open IOF xml'), _('IOF xml (*.xml)'))
        if file_name is not '':
            try:
                iof_xml.import_from_iof(file_name)
            except Exception as e:
                logging.exception(str(e))
                QMessageBox.warning(self.app, _('Error'), _('Import error') + ': ' + file_name)
            self.app.init_model()


class AddObjectAction(Action):
    def execute(self):
        self.app.add_object()


class DeleteAction(Action):
    def execute(self):
        self.app.delete_object()


class TextExchangeAction(Action):
    def execute(self):
        TextExchangeDialog().exec_()
        self.app.refresh()


class MassEditAction(Action):
    def execute(self):
        if self.app.current_tab == 0:
            MassEditDialog().exec_()
            self.app.refresh()


class RefreshAction(Action):
    def execute(self):
        self.app.refresh()


class FilterAction(Action):
    def execute(self):
        if self.app.current_tab not in range(2):
            return
        table = self.app.get_current_table()
        DialogFilter(table).exec_()
        self.app.refresh()


class SearchAction(Action):
    def execute(self):
        if self.app.current_tab not in range(5):
            return
        table = self.app.get_current_table()
        SearchDialog(table).exec_()
        self.app.refresh()


class ToStartPreparationAction(Action):
    def execute(self):
        self.app.select_tab(0)


class ToRaceResultsAction(Action):
    def execute(self):
        self.app.select_tab(1)


class ToGroupsAction(Action):
    def execute(self):
        self.app.select_tab(2)


class ToCoursesAction(Action):
    def execute(self):
        self.app.select_tab(3)


class ToTeamsAction(Action):
    def execute(self):
        self.app.select_tab(4)


class StartPreparationAction(Action):
    def execute(self):
        StartPreparationDialog().exec_()
        self.app.refresh()


class GuessCoursesAction(Action):
    def execute(self):
        guess_courses_for_groups()
        self.app.refresh()


class GuessCorridorsAction(Action):
    def execute(self):
        guess_corridors_for_groups()
        self.app.refresh()


class RelayNumberAction(Action):
    def execute(self):
        if self.app.relay_number_assign:
            self.app.relay_number_assign = False
            QApplication.restoreOverrideCursor()
        else:
            self.app.relay_number_assign = True
            QApplication.setOverrideCursor(QtCore.Qt.PointingHandCursor)
            RelayNumberDialog().exec_()
        self.app.refresh()


class NumberChangeAction(Action):
    def execute(self):
        NumberChangeDialog().exec_()
        self.app.refresh()


class StartTimeChangeAction(Action):
    def execute(self):
        StartTimeChangeDialog().exec_()
        self.app.refresh()


class StartHandicapAction(Action):
    def execute(self):
        StartHandicapDialog().exec_()
        self.app.refresh()


class RelayCloneAction(Action):
    def execute(self):
        RelayCloneDialog().exec_()
        self.app.refresh()


class CopyBibToCardNumber(Action):
    def execute(self):
        msg = _('Use bib as card number') + '?'
        reply = messageBoxQuestion(self.app, _('Question'), msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            copy_bib_to_card_number()
            self.app.refresh()


class CopyCardNumberToBib(Action):
    def execute(self):
        msg = _('Use card number as bib') + '?'
        reply = messageBoxQuestion(self.app, _('Question'), msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            copy_card_number_to_bib()
            self.app.refresh()


class ManualFinishAction(Action):
    def execute(self):
        result = race().new_result(ResultManual)
        Teamwork().send(result.to_dict())
        race().add_new_result(result)
        logging.info(_('Manual finish'))
        self.app.refresh()


class SPORTidentReadoutAction(Action):
    def execute(self):
        SIReaderClient().toggle()
        time.sleep(0.5)
        self.app.interval()


class SportiduinoReadoutAction(Action):
    def execute(self):
        SportiduinoClient().toggle()
        time.sleep(0.5)
        self.app.interval()


class SFRReadoutAction(Action):
    def execute(self):
        SFRReaderClient().toggle()
        time.sleep(0.5)
        self.app.interval()


class CreateReportAction(Action):
    def execute(self):
        ReportDialog().exec_()


class SplitPrintoutAction(Action):
    def execute(self):
        self.app.split_printout_selected()


class RecheckingAction(Action):
    def execute(self):
        ResultChecker.check_all()
        ResultCalculation(race()).process_results()
        self.app.refresh()


class GroupFinderAction(Action):
    def execute(self):
        obj = race()
        indices = self.app.get_selected_rows()
        results = obj.results
        for index in indices:
            if index < 0:
                continue
            if index >= len(results):
                break
            result = results[index]
            if result.person and result.status in [ResultStatus.MISSING_PUNCH]:
                for group in obj.groups:
                    if result.check(group.course):
                        result.person.group = group
                        result.status = ResultStatus.OK
                        break
        self.app.refresh()


class PenaltyCalculationAction(Action):
    def execute(self):
        logging.debug('Penalty calculation start')
        for result in race().results:
            if result.person is not None:
                ResultChecker.calculate_penalty(result)
        logging.debug('Penalty calculation finish')
        ResultCalculation(race()).process_results()
        self.app.refresh()


class PenaltyRemovingAction(Action):
    def execute(self):
        logging.debug('Penalty removing start')
        for result in race().results:
            result.penalty_time = OTime(msec=0)
            result.penalty_laps = 0
        logging.debug('Penalty removing finish')
        ResultCalculation(race()).process_results()
        self.app.refresh()


class ChangeStatusAction(Action):
    def execute(self):
        if self.app.current_tab != 1:
            logging.warning(_('No result selected'))
            return
        obj = race()

        status_dict = {
            ResultStatus.NONE: ResultStatus.OK,
            ResultStatus.OK: ResultStatus.DISQUALIFIED,
            ResultStatus.DISQUALIFIED: ResultStatus.DID_NOT_START,
            ResultStatus.DID_NOT_START: ResultStatus.DID_NOT_FINISH,
            ResultStatus.DID_NOT_FINISH: ResultStatus.RESTORED,
            ResultStatus.RESTORED: ResultStatus.OK,
        }

        table = self.app.get_result_table()
        assert isinstance(table, QTableView)
        index = table.currentIndex().row()
        if index < 0:
            index = 0
        if index >= len(obj.results):
            mes = QMessageBox()
            mes.setText(_('No results to change status'))
            mes.exec_()
            return
        result = obj.results[index]
        if result.status in status_dict:
            result.status = status_dict[result.status]
        else:
            result.status = ResultStatus.OK
        Teamwork().send(result.to_dict())
        self.app.refresh()


class SetDNSNumbersAction(Action):
    def execute(self):
        NotStartDialog().exec_()
        self.app.refresh()


class CPDeleteAction(Action):
    def execute(self):
        CPDeleteDialog().exec_()
        self.app.refresh()


class AddSPORTidentResultAction(Action):
    def execute(self):
        result = race().new_result()
        race().add_new_result(result)
        Teamwork().send(result.to_dict())
        logging.info('SPORTident result')
        self.app.get_result_table().model().init_cache()
        self.app.refresh()


class TimekeepingSettingsAction(Action):
    def execute(self):
        TimekeepingPropertiesDialog().exec_()
        self.app.refresh()


class TeamworkSettingsAction(Action):
    def execute(self):
        TeamworkPropertiesDialog().exec_()


class TeamworkEnableAction(Action):
    def execute(self):
        host = race().get_setting('teamwork_host', 'localhost')
        port = race().get_setting('teamwork_port', 50010)
        token = race().get_setting('teamwork_token', str(uuid.uuid4())[:8])
        connection_type = race().get_setting('teamwork_type_connection', 'client')
        Teamwork().set_options(host, port, token, connection_type)
        Teamwork().toggle()
        time.sleep(0.5)
        self.app.interval()


class TeamworkSendAction(Action):
    def execute(self):
        try:
            obj = race()
            data_list = [obj.persons, obj.results, obj.groups, obj.courses, obj.organizations]
            if not self.app.current_tab < len(data_list):
                return
            items = data_list[self.app.current_tab]
            indexes = self.app.get_selected_rows()
            items_dict = []
            for index in indexes:
                if index < 0:
                    continue
                if index >= len(items):
                    break
                items_dict.append(items[index].to_dict())
            Teamwork().send(items_dict)
        except Exception as e:
            logging.error(str(e))


class PrinterSettingsAction(Action):
    def execute(self):
        PrintPropertiesDialog().exec_()


class LiveSettingsAction(Action):
    def execute(self):
        LiveDialog().exec_()
        self.app.refresh()


class TelegramSettingsAction(Action):
    def execute(self):
        TelegramDialog().exec_()


class TelegramSendAction(Action):
    def execute(self):
        try:
            if not self.app.current_tab == 1:
                logging.warning(_('No result selected'))
                return
            items = race().results
            indexes = self.app.get_selected_rows()
            for index in indexes:
                if index < 0:
                    continue
                if index >= len(items):
                    pass
                TelegramClient().send_result(items[index])
        except Exception as e:
            logging.error(str(e))


class AboutAction(Action):
    def execute(self):
        AboutDialog().exec_()


class CheckUpdatesAction(Action):
    def execute(self):
        try:
            if not checker.check_version(config.VERSION):
                message = _('Update available') + ' ' + checker.get_version()
            else:
                message = _('You are using the latest version')

            QMessageBox.information(self.app, _('Info'), message)
        except Exception as e:
            logging.error(str(e))
            QMessageBox.warning(self.app, _('Error'), str(e))


class TestingAction(Action):
    def execute(self):
        testing.test()


class AssignResultByBibAction(Action):
    def execute(self):
        for result in race().results:
            if result.person is None and result.bib:
                result.person = find(race().persons, bib=result.bib)
        self.app.refresh()


class AssignResultByCardNumberAction(Action):
    def execute(self):
        for result in race().results:
            if result.person is None and result.card_number:
                result.person = find(race().persons, card_number=result.card_number)
        self.app.refresh()


class ImportSportOrgAction(Action):
    def execute(self):
        file_name = get_open_file_name(_('Open SportOrg json'), _('SportOrg (*.json)'))
        if file_name is not '':
            with open(file_name) as f:
                attr = get_races_from_file(f)
            SportOrgImportDialog(*attr).exec_()
            self.app.refresh()


class RentCardsAction(Action):
    def execute(self):
        RentCardsDialog().exec_()
        self.app.refresh()


__all__ = [
    'NewAction',
    'SaveAction',
    'OpenAction',
    'SaveAsAction',
    'OpenRecentAction',
    'CopyAction',
    'DuplicateAction',
    'SettingsAction',
    'EventSettingsAction',
    'MassEditAction',
    'CSVWinorientImportAction',
    'WDBWinorientImportAction',
    'OcadTXTv8ImportAction',
    'WDBWinorientExportAction',
    'IOFResultListExportAction',
    'AddObjectAction',
    'DeleteAction',
    'TextExchangeAction',
    'RefreshAction',
    'FilterAction',
    'SearchAction',
    'ToStartPreparationAction',
    'ToRaceResultsAction',
    'ToGroupsAction',
    'ToCoursesAction',
    'ToTeamsAction',
    'StartPreparationAction',
    'GuessCoursesAction',
    'GuessCorridorsAction',
    'RelayNumberAction',
    'NumberChangeAction',
    'StartTimeChangeAction',
    'StartHandicapAction',
    'RelayCloneAction',
    'CopyBibToCardNumber',
    'CopyCardNumberToBib',
    'ManualFinishAction',
    'SPORTidentReadoutAction',
    'SportiduinoReadoutAction',
    'SFRReadoutAction',
    'CreateReportAction',
    'SplitPrintoutAction',
    'RecheckingAction',
    'PenaltyCalculationAction',
    'PenaltyRemovingAction',
    'ChangeStatusAction',
    'SetDNSNumbersAction',
    'CPDeleteAction',
    'AddSPORTidentResultAction',
    'TimekeepingSettingsAction',
    'TeamworkSettingsAction',
    'PrinterSettingsAction',
    'LiveSettingsAction',
    'AboutAction',
    'TestingAction',
    'TeamworkEnableAction',
    'TeamworkSendAction',
    'TelegramSettingsAction',
    'TelegramSendAction',
    'IOFEntryListImportAction',
    'CheckUpdatesAction',
    'AssignResultByBibAction',
    'AssignResultByCardNumberAction',
    'ImportSportOrgAction',
    'RentCardsAction',
    'GroupFinderAction',
]
