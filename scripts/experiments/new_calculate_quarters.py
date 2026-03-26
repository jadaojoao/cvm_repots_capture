    def calculate_quarters(self, df, report_type):
        """
        Pivot LONG format to WIDE format.
        
        Input: LONG DataFrame with 1 row per account+period after VERSION filtering
        Output: WIDE DataFrame with 1 row per account, columns per period
        
        Args:
            df: LONG format DataFrame with LINE_ID_BASE, period columns, VL_CONTA
            report_type: 'BPA', 'BPP', 'DRE', or 'DFC'
            
        Returns:
            WIDE format DataFrame
        """
        if df.empty:
            return pd.DataFrame()
        
        # Ensure dates are datetime
        if 'DT_REFER' in df.columns:
            df['DT_REFER'] = pd.to_datetime(df['DT_REFER'], errors='coerce')
        if 'DT_INI_EXERC' in df.columns:
            df['DT_INI_EXERC'] = pd.to_datetime(df['DT_INI_EXERC'], errors='coerce')
        if 'DT_FIM_EXERC' in df.columns:
            df['DT_FIM_EXERC'] = pd.to_datetime(df['DT_FIM_EXERC'], errors='coerce')
        
        # Create period label column
        df = df.copy()
        df['PERIOD_LABEL'] = df.apply(lambda row: self._create_period_label(row, report_type), axis=1)
        
        # Remove rows with no valid period label
        df = df[df['PERIOD_LABEL'].notna()]
        
        if df.empty:
            return pd.DataFrame()
        
        # Prepare index columns - use LINE_ID_BASE (stable account ID)
        index_cols = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA']
        
        # Prepare metadata to preserve
        metadata_dict = {}
        for col in ['DS_CONTA_norm']:
            if col in df.columns:
                # Get one value per LINE_ID_BASE
                metadata_dict[col] = df.groupby('LINE_ID_BASE')[col].first()
        
        # Pivot: index=account, columns=period, values=VL_CONTA
        df_wide = df.pivot_table(
            index=index_cols,
            columns='PERIOD_LABEL',
            values='VL_CONTA',
            aggfunc='first'  # Should be only 1 value after VERSION filter
        )
        
        # Reset index to make LINE_ID_BASE, CD_CONTA, DS_CONTA regular columns
        df_wide = df_wide.reset_index()
        
        # Add metadata columns
        for col_name, series in metadata_dict.items():
            df_wide[col_name] = df_wide['LINE_ID_BASE'].map(series)
        
        # Add QA_CONFLICT column (False for all - conflicts would be in QA_Errors)
        df_wide['QA_CONFLICT'] = False
        
        # Sort columns: metadata first, then periods chronologically
        metadata_cols = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']
        metadata_cols_present = [c for c in metadata_cols if c in df_wide.columns]
        
        period_cols = [c for c in df_wide.columns if c not in metadata_cols_present]
        period_cols_sorted = sorted(period_cols, key=lambda x: self._period_sort_key(x))
        
        final_cols = metadata_cols_present + period_cols_sorted
        df_wide = df_wide[final_cols]
        
        return df_wide
    
    def _create_period_label(self, row, report_type):
        """
        Create period label like '1Q24', '2Q24', '2024' from date columns.
        """
        if report_type in ['BPA', 'BPP']:
            # Use DT_REFER
            dt = row.get('DT_REFER')
            if pd.isna(dt):
                return None
            
            year = dt.year
            yy = str(year)[2:]
            month = dt.month
            
            # Quarter labels
            if month == 3:
                return f'1Q{yy}'
            elif month == 6:
                return f'2Q{yy}'
            elif month == 9:
                return f'3Q{yy}'
            elif month == 12:
                return str(year)  # Annual
            else:
                return None
        
        else:  # DRE, DFC
            # Use DT_INI_EXERC and DT_FIM_EXERC
            dt_ini = row.get('DT_INI_EXERC')
            dt_fim = row.get('DT_FIM_EXERC')
            
            if pd.isna(dt_ini) or pd.isna(dt_fim):
                return None
            
            year = dt_fim.year
            yy = str(year)[2:]
            
            # Check if it's a quarter or annual
            if dt_ini.month == 1 and dt_ini.day == 1:
                if dt_fim.month == 3 and dt_fim.day == 31:
                    return f'1Q{yy}'
                elif dt_fim.month == 6 and dt_fim.day == 30:
                    # Could be 2Q (Apr-Jun) or YTD 6M
                    # Check if start is Jan or Apr
                    return f'2Q{yy}'  # Simplified - assume quarterly
                elif dt_fim.month == 9 and dt_fim.day == 30:
                    return f'3Q{yy}'  # Simplified  
                elif dt_fim.month == 12 and dt_fim.day == 31:
                    return str(year)  # Annual
            
            elif dt_ini.month == 4 and dt_fim.month == 6:
                return f'2Q{yy}'
            elif dt_ini.month == 7 and dt_fim.month == 9:
                return f'3Q{yy}'
            elif dt_ini.month == 10 and dt_fim.month == 12:
                return f'4Q{yy}'
            
            return None  # Unrecognized period
    
    def _period_sort_key(self, period_label):
        """
        Create sort key for period labels to order chronologically.
        Examples: '1Q21' < '2Q21' < '3Q21' < '4Q21' < '2021' < '1Q22'
        """
        if not period_label or not isinstance(period_label, str):
            return (9999, 0)
        
        # Annual format: '2021', '2022', etc.
        if period_label.isdigit() and len(period_label) == 4:
            year = int(period_label)
            return (year, 5)  # Annual comes after Q4
        
        # Quarterly format: '1Q21', '2Q21', etc.
        if len(period_label) >= 3 and period_label[0].isdigit() and period_label[1] == 'Q':
            quarter = int(period_label[0])
            year_part = period_label[2:]
            if year_part.isdigit():
                if len(year_part) == 2:
                    year = 2000 + int(year_part)
                else:
                    year = int(year_part)
                return (year, quarter)
        
        # Unknown format - put at end
        return (9999, 0)
