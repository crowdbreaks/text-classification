from utils.helpers import find_project_root
import pandas as pd
import os
import glob
import json

class ListRuns:
    def __init__(self):
        self.header = 'List runs\n----------\n\n'

    def list_runs(self, model=None, pattern=None, filename_pattern=None, params=None, metrics=None, averaging='macro', names_only=False, top=40, all_params=False):
        # set some display options
        pd.set_option('display.max_rows', 300)
        # pd.set_option('display.max_columns', 100)
        # pd.set_option('display.width', 400)
        default_params = ['model', 'learning_rate', 'num_epochs']
        default_metrics = ['f1', 'accuracy', 'precision', 'recall']
        # metrics
        if metrics is None:
            metrics = default_metrics
        for i, m in enumerate(metrics):
            if m in ['f1', 'precision', 'recall']:
                metrics[i] = '{}_{}'.format(m, averaging)
        # read data
        df = self.load_data(model=model, pattern=pattern, filename_pattern=filename_pattern)
        # format sci numbers
        df = self.format_cols(df)
        # params
        if params is not None:
            df = df[params + metrics]
        else:
            if all_params:
                # show everything apart from meaningless params
                df = df[df.columns.drop(list(df.filter(regex='path')))]
                df = df[df.columns.drop(['overwrite', 'write_test_output'])]
                df = df[df.columns.drop(list(set(df.filter(regex='|'.join(default_metrics))) - set(metrics)))]
            else:
                # use default
                cols = []
                for _p in default_params + metrics:
                    if _p in df:
                        cols.append(_p)
                df = df[cols]
        if len(df) == 0:
            return
        if top < 0:
            top = None # show all entries
        df = df.sort_values(metrics, ascending=False)[:top]
        print(self.header)
        if names_only:
            print('\n'.join(df.index))
        else:
            print(df)

    def load_data(self, model=None, pattern=None, filename_pattern=None):
        df = self.collect_results()
        if len(df) == 0:
            raise FileNotFoundError('No output data run models could be found.')
        df.set_index('name', inplace=True)
        if pattern is not None:
            self.header += self.add_key_value('Pattern', pattern)
            df = df[df.index.str.contains(r'{}'.format(pattern))]
            if len(df) == 0:
                raise ValueError('No runs to list under given pattern {}'.format(pattern))
        if filename_pattern is not None:
            self.header += self.add_key_value('Filename pattern', filename_pattern)
            df = df[df.train_data.str.contains(filename_pattern)]
            if len(df) == 0:
                raise ValueError('No runs to list under given filename pattern {}'.format(filename_pattern))
        if model is not None:
            self.header += self.add_key_value('Model', model)
            df = df[df.model == model]
        df.dropna(axis=1, how='all', inplace=True)
        return df

    def format_cols(self, df):
        int_cols = ['num_epochs', 'n_grams', 'train_batch_size', 'test_batch_size']
        for int_col in int_cols:
            try:
                df[int_col] = df[int_col].astype('Int64', errors='ignore')
            except KeyError:
                continue
        sci_fmt_cols = ['learning_rate']
        for col in df:
            if col in sci_fmt_cols:
                df[col] = df[col].apply(lambda s: '{:.0e}'.format(s))
        return df

    def collect_results(self, run='*'):
        run_path = os.path.join(find_project_root(), 'modeling', 'output', run)
        folders = glob.glob(run_path)
        results = []
        for f in folders:
            if os.path.isdir(f):
                config_path = os.path.join(f, 'run_config.json')
                test_output_path = os.path.join(f, 'test_output.json')
                try:
                    with open(config_path, 'r') as f_p:
                        run_config = json.load(f_p)
                    with open(test_output_path, 'r') as f_p:
                        test_output = json.load(f_p)
                except FileNotFoundError:
                    continue
                results.append({**run_config, **test_output})
        return pd.DataFrame(results)

    def add_key_value(self, key, value, fmt='', width=12, filler=0, unit=''):
        return '- {}:{}{:>{width}{fmt}}{unit}\n'.format(key, max(0, filler - len(key))*' ', value, width=width, fmt=fmt, unit=' '+unit)
