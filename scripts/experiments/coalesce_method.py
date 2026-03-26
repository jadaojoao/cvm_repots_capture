    def coalesce_duplicate_line_ids(self, df_wide, statement_type):
        """
        Merge duplicate LINE_ID_BASEs in WIDE format by coalescing period columns.
        
        For each LINE_ID_BASE group:
        - Coalesce period columns (first non-null value)
        - Detect real conflicts (same period, different non-null values)
        - Choose canonical DS_CONTA (longest/most complete)
        
        Args:
            df_wide: WIDE format DataFrame (1+ rows per LINE_ID_BASE)
            statement_type: 'BPA', 'BPP', 'DRE', or 'DFC'
            
        Returns:
            tuple: (coalesced_df with 1 row per LINE_ID_BASE, qa_log list, qa_errors list)
        """
        import re
        
        qa_log = []
        qa_errors = []
        
        if df_wide.empty or 'LINE_ID_BASE' not in df_wide.columns:
            return df_wide, qa_log, qa_errors
        
        # Identify period columns (regex: ^(\dQ\d{2}|\d{4})$)
        period_pattern = re.compile(r'^(\dQ\d{2}|\d{4})$')
        period_cols = [col for col in df_wide.columns if period_pattern.match(str(col))]
        
        # Metadata columns
        metadata_cols = ['LINE_ID_BASE', 'CD_CONTA', 'DS_CONTA', 'DS_CONTA_norm', 'QA_CONFLICT']
        metadata_cols = [c for c in metadata_cols if c in df_wide.columns]
        
        # Find duplicates
        dup_counts = df_wide.groupby('LINE_ID_BASE').size()
        duplicate_ids = dup_counts[dup_counts > 1].index.tolist()
        
        if not duplicate_ids:
            print(f"    No duplicate LINE_ID_BASEs in {statement_type} - already unique")
            return df_wide, qa_log, qa_errors
        
        print(f"    Coalescing {len(duplicate_ids)} duplicate LINE_ID_BASEs in {statement_type}...")
        
        coalesced_rows = []
        rows_to_remove = []
        conflicts_detected = 0
        
        for line_id_base in duplicate_ids:
            dup_group = df_wide[df_wide['LINE_ID_BASE'] == line_id_base].copy()
            dup_indices = dup_group.index.tolist()
            
            # Start with first row as template
            merged_row = dup_group.iloc[0].copy()
            
            # Track conflicts
            has_conflict = False
            conflict_periods = []
            
            # Coalesce each period column
            for period_col in period_cols:
                non_null_values = dup_group[period_col].dropna()
                
                if len(non_null_values) == 0:
                    # No data for this period
                    merged_row[period_col] = None
                elif len(non_null_values) == 1:
                    # Single value - no conflict
                    merged_row[period_col] = non_null_values.iloc[0]
                else:
                    # Multiple values - check if they're different
                    unique_values = non_null_values.unique()
                    
                    if len(unique_values) == 1:
                        # All same value - no conflict
                        merged_row[period_col] = unique_values[0]
                    else:
                        # REAL CONFLICT: different values for same period
                        has_conflict = True
                        conflict_periods.append(period_col)
                        merged_row[period_col] = non_null_values.iloc[0]  # Take first
                        
                        qa_errors.append({
                            'type': 'REAL_CONFLICT',
                            'statement': statement_type,
                            'line_id_base': str(line_id_base),
                            'period': period_col,
                            'values': unique_values.tolist(),
                            'descriptions': dup_group['DS_CONTA'].unique().tolist(),
                            'action': 'MANUAL REVIEW REQUIRED - same period has different values'
                        })
            
            # Choose canonical DS_CONTA
            # Prefer row with most periods filled
            periods_filled = dup_group[period_cols].notna().sum(axis=1)
            max_filled_idx = periods_filled.idxmax()
            
            # If tied, prefer longest DS_CONTA
            tied_rows = dup_group[periods_filled == periods_filled.max()]
            if len(tied_rows) > 1:
                ds_conta_lengths = tied_rows['DS_CONTA'].str.len()
                canonical_idx = ds_conta_lengths.idxmax()
            else:
                canonical_idx = max_filled_idx
            
            merged_row['DS_CONTA'] = dup_group.loc[canonical_idx, 'DS_CONTA']
            merged_row['CD_CONTA'] = dup_group.loc[canonical_idx, 'CD_CONTA']
            
            # Preserve DS_CONTA_norm from first row
            if 'DS_CONTA_norm' in dup_group.columns:
                merged_row['DS_CONTA_norm'] = dup_group['DS_CONTA_norm'].iloc[0]
            
            # Set QA_CONFLICT flag
            merged_row['QA_CONFLICT'] = has_conflict
            
            if has_conflict:
                conflicts_detected += 1
            
            coalesced_rows.append(merged_row)
            rows_to_remove.extend(dup_indices)
            
        # Build final DataFrame
        df_clean = df_wide.drop(index=rows_to_remove)
        df_coalesced = pd.DataFrame(coalesced_rows)
        df_final = pd.concat([df_clean, df_coalesced], ignore_index=True)
        
        # Log
        qa_log.append({
            'type': 'COALESCE_DUPLICATES',
            'statement': statement_type,
            'duplicates_found': len(duplicate_ids),
            'conflicts_detected': conflicts_detected,
            'action': f'Merged {len(duplicate_ids)} duplicate LINE_ID_BASEs by coalescing periods'
        })
        
        print(f"      Merged {len(duplicate_ids)} duplicates ({conflicts_detected} had real conflicts)")
        
        return df_final, qa_log, qa_errors
