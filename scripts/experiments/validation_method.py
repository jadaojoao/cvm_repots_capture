    def validate_final_output(self, processed_reports):
        """
        Validate final output for regression testing (Priority 2 protection).
        
        Checks:
        1. LINE_ID_BASE uniqueness per sheet
        2. DS_CONTA_norm no nulls
        3. LINE_ID_BASE contains no '#' characters
        4. QA_CONFLICT not 100% True
        5. CD_CONTA no nulls
        
        Args:
            processed_reports: Dictionary of processed DataFrames
            
        Returns:
            tuple: (is_valid bool, errors list of dicts)
        """
        errors = []
        
        for sheet_name, df in processed_reports.items():
            if df.empty:
                continue
            
            # Reset index if needed to access columns
            if 'LINE_ID_BASE' not in df.columns:
                df = df.reset_index()
            
            # 1. LINE_ID_BASE Uniqueness
            line_id_counts = df['LINE_ID_BASE'].value_counts()
            duplicates = line_id_counts[line_id_counts > 1]
            if len(duplicates) > 0:
                errors.append({
                    'type': 'REGRESSION_TEST_FAILED',
                    'test': 'LINE_ID_BASE_UNIQUENESS',
                    'statement': sheet_name,
                    'error': f'{len(duplicates)} duplicate LINE_ID_BASEs found',
                    'sample': duplicates.head(5).to_dict()
                })
            
            # 2. DS_CONTA_norm No Nulls
            if 'DS_CONTA_norm' in df.columns:
                null_count = df['DS_CONTA_norm'].isna().sum()
                if null_count > 0:
                    errors.append({
                        'type': 'REGRESSION_TEST_FAILED',
                        'test': 'DS_CONTA_NORM_NO_NULLS',
                        'statement': sheet_name,
                        'error': f'{null_count} null values in DS_CONTA_norm',
                        'percentage': f'{null_count/len(df)*100:.1f}%'
                    })
            
            # 3. LINE_ID_BASE No '#' Characters
            hash_count = df['LINE_ID_BASE'].astype(str).str.contains('#', na=False).sum()
            if hash_count > 0:
                errors.append({
                    'type': 'REGRESSION_TEST_FAILED',
                    'test': 'LINE_ID_BASE_NO_HASH',
                    'statement': sheet_name,
                    'error': f'{hash_count} LINE_ID_BASEs contain "#" character',
                    'sample': df[df['LINE_ID_BASE'].astype(str).str.contains('#', na=False)]['LINE_ID_BASE'].head(5).tolist()
                })
            
            # 4. QA_CONFLICT Not 100% True
            if 'QA_CONFLICT' in df.columns:
                conflict_count = (df['QA_CONFLICT'] == True).sum()
                conflict_pct = conflict_count / len(df) * 100
                if conflict_pct >= 100.0:
                    errors.append({
                        'type': 'REGRESSION_TEST_FAILED',
                        'test': 'QA_CONFLICT_NOT_100_PCT',
                        'statement': sheet_name,
                        'error': f'QA_CONFLICT is {conflict_pct:.1f}% True (100% indicates broken logic)',
                        'count': int(conflict_count),
                        'total': len(df)
                    })
            
            # 5. CD_CONTA No Nulls
            if 'CD_CONTA' in df.columns:
                null_count = df['CD_CONTA'].isna().sum()
                if null_count > 0:
                    errors.append({
                        'type': 'REGRESSION_TEST_FAILED',
                        'test': 'CD_CONTA_NO_NULLS',
                        'statement': sheet_name,
                        'error': f'{null_count} null values in CD_CONTA',
                        'percentage': f'{null_count/len(df)*100:.1f}%'
                    })
        
        is_valid = len(errors) == 0
        return is_valid, errors
