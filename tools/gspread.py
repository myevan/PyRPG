import logging
import gspread
import os

from framework.env import EnvironConfig

class Workbook:
    logger = logging.getLogger('gspread')

    def __init__(self) -> None:
        self.client = gspread.service_account()
        self.work = None

    def open(self, book_name):
        self.logger.debug('open', book=book_name)
        self.book = self.client.open(book_name)

    def gen_file_path(self, out, ext='csv'):
        if out:
            if os.path.isfile(out):
                return os.path.realpath(out)
            elif os.path.isdir(out):
                return os.path.realpath(os.path.join(out, f'{self.book.title}.{ext}'))
            else:
                raise ValueError('UNKNOWN_PATH', out)
        else:
            env_cfg = EnvironConfig.get()
            return os.path.join(env_cfg.CODE_PROJECT_DIR_PATH, f'{self.book.title}.{ext}')

    def export_sheet(self, out_file_path, sheet_name=''):
        self.logger.debug('export', sheet=sheet_name, out=out_file_path)

        sheet = self.book.worksheet(sheet_name) if sheet_name else self.book.get_worksheet(0)
        rows = sheet.get_all_values()

        with open(out_file_path, 'w', encoding='utf-8-sig', newline='') as out_file:
            import csv
            csv_writer = csv.writer(out_file)
            csv_writer.writerows(rows)
