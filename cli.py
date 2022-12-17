import click
import logging

@click.group()
@click.option('--debug', is_flag=True, default=False, help='Show debug log messages.')
@click.pass_context
def cli(ctx, debug):
    ctx.ensure_object(dict)

    from core.app import Application
    app = Application(logging_level=logging.DEBUG if debug else logging.INFO)
    ctx.obj['APP'] = app

# https://docs.gspread.org/en/latest/oauth2.html#enable-api-access
# * windows: %APPDATA%\gspread\service_account.json
# * posix: ~/.config/gspread/service_account.json
#
# gspread.exceptions.SpreadSheetNotFound: Share `client_email` in google spread sheet
# gspread.exceptions.APIError: Enable Google Sheets API 
#
@cli.command()
@click.argument('name', type=str)
@click.option('--out', type=str)
def gspread_csv(name, out):
    from tools.gspread_tool import Workbook

    book = Workbook()
    book.open(name)
    out_file_path = book.gen_file_path(out, ext='csv')
    book.export_sheet(out_file_path, sheet_name='csv')

if __name__ == '__main__':
    cli()
