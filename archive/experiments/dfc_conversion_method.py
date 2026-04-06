    def convert_dfc_ytd_to_standalone(self, df_wide, statement_type):
        """
        Convert DFC from YTD (cumulative) values to standalone quarterly values.
        
        DFC ITR values are typically YTD:
        - 1Q = YTD 3M
        - 2Q_ytd = YTD 6M  
        - 3Q_ytd = YTD 9M
        
        We need standalone quarters:
        - 1Q = YTD_1Q (direct)
        - 2Q = YTD_2Q - YTD_1Q
        - 3Q = YTD_3Q - YTD_2Q
        - 4Q = YYYY - YTD_3Q (prefer annual from DFP)
        - YYYY = annual value (untouched)
        
        Args:
            df_wide: WIDE format DataFrame with period columns
            statement_type: 'DFC' or 'DRE'
            
        Returns:
            tuple: (df_converted, qa_errors list)
        """
        import re
        
        qa_errors = []
        
        if df_wide.empty:
            return df_wide, qa_errors
        
        # Identify period columns
        period_pattern = re.compile(r'^(\dQ\d{2}|\d{4})$')
        period_cols = [col for col in df_wide.columns if period_pattern.match(str(col))]
        
        # Group by year
        year_pattern = re.compile(r'^\d{4}$')
        annual_cols = [col for col in period_cols if year_pattern.match(col)]
        
        # Extract unique years
        years = set()
        for col in period_cols:
            if re.match(r'^\dQ(\d{2})$', col):
                yy = col[-2:]
                year = int('20' + yy) if int(yy) < 50 else int('19' + yy)
                years.add(year)
        for col in annual_cols:
            years.add(int(col))
        
        years = sorted(years)
        
        print(f"    Converting {statement_type} from YTD to standalone for years: {years}")
        
        df_converted = df_wide.copy()
        
        for year in years:
            yy = str(year)[2:]
            
            # Column names
            col_1q = f'1Q{yy}'
            col_2q = f'2Q{yy}'
            col_3q = f'3Q{yy}'
            col_4q = f'4Q{yy}'
            col_annual = str(year)
            
            # Check which columns exist
            has_1q = col_1q in df_converted.columns
            has_2q = col_2q in df_converted.columns
            has_3q = col_3q in df_converted.columns
            has_4q = col_4q in df_converted.columns
            has_annual = col_annual in df_converted.columns
            
            if not any([has_1q, has_2q, has_3q, has_4q, has_annual]):
                continue  # No data for this year
            
            # Store original YTD values
            ytd_1q = df_converted[col_1q].copy() if has_1q else pd.Series([None] * len(df_converted))
            ytd_2q = df_converted[col_2q].copy() if has_2q else pd.Series([None] * len(df_converted))
            ytd_3q = df_converted[col_3q].copy() if has_3q else pd.Series([None] * len(df_converted))
            annual = df_converted[col_annual].copy() if has_annual else pd.Series([None] * len(df_converted))
            
            # Convert to standalone
            # 1Q stays as-is (already standalone for 3M period)
            standalone_1q = ytd_1q if has_1q else pd.Series([None] * len(df_converted))
            
            # 2Q = YTD_2Q - YTD_1Q
            if has_2q and has_1q:
                standalone_2q = ytd_2q - ytd_1q
            elif has_2q:
                # Have 2Q but no 1Q - assume it's already standalone (rare)
                standalone_2q = ytd_2q
            else:
                standalone_2q = pd.Series([None] * len(df_converted))
            
            # 3Q = YTD_3Q - YTD_2Q
            if has_3q and has_2q:
                standalone_3q = ytd_3q - ytd_2q
            elif has_3q:
                # Have 3Q but no 2Q - can't reliably convert
                standalone_3q = ytd_3q  # Keep as-is but log warning
                qa_errors.append({
                    'type': 'DFC_CONVERSION_WARNING',
                    'statement': statement_type,
                    'year': year,
                    'issue': '3Q present but 2Q missing - cannot convert to standalone',
                    'action': 'Kept YTD value for 3Q'
                })
            else:
                standalone_3q = pd.Series([None] * len(df_converted))
            
            # 4Q = ANNUAL - YTD_3Q (prefer annual source)
            if has_annual and has_3q:
                standalone_4q = annual - ytd_3q
            elif has_4q:
                # Have 4Q column but no annual - keep as-is
                standalone_4q = df_converted[col_4q] if has_4q else pd.Series([None] * len(df_converted))
            else:
                standalone_4q = pd.Series([None] * len(df_converted))
                
                # Log missing 4Q
                qa_errors.append({
                    'type': 'MISSING_4Q',
                    'statement': statement_type,
                    'year': year,
                    'issue': 'No 4Q data available (neither via annual-3Q nor standalone 4Q)',
                    'action': '4Q column will be empty for this year'
                })
            
            # Update DataFrame with standalone values
            if has_1q:
                df_converted[col_1q] = standalone_1q
            if has_2q:
                df_converted[col_2q] = standalone_2q
            if has_3q:
                df_converted[col_3q] = standalone_3q
            
            # Add or update 4Q column
            if standalone_4q.notna().any():
                df_converted[col_4q] = standalone_4q
            
            # Validation: sum(1Q+2Q+3Q+4Q) == YYYY (with tolerance)
            if has_annual:
                quarterly_sum = standalone_1q.fillna(0) + standalone_2q.fillna(0) + standalone_3q.fillna(0) + standalone_4q.fillna(0)
                diff = (quarterly_sum - annual).abs()
                tolerance = 0.01  # 0.01 million BRL
                
                # Find accounts with significant differences
                problematic = diff[diff > tolerance]
                if len(problematic) > 0:
                    for idx in problematic.index[:5]:  # Log first 5
                        line_id = df_converted.loc[idx, 'LINE_ID_BASE'] if 'LINE_ID_BASE' in df_converted.columns else 'Unknown'
                        qa_errors.append({
                            'type': 'DFC_VALIDATION_FAILED',
                            'statement': statement_type,
                            'year': year,
                            'line_id_base': str(line_id),
                            'quarterly_sum': float(quarterly_sum.loc[idx]),
                            'annual': float(annual.loc[idx]),
                            'difference': float(diff.loc[idx]),
                            'action': 'MANUAL REVIEW - quarterly sum does not match annual'
                        })
                        
                        # Mark QA_CONFLICT
                        if 'QA_CONFLICT' in df_converted.columns:
                            df_converted.loc[idx, 'QA_CONFLICT'] = True
                    
                    print(f"      ⚠️ {len(problematic)} accounts failed sum validation for {year}")
        
        print(f"      Converted {len(years)} years to standalone values")
        
        return df_converted, qa_errors
