from .utils import is_number, format_num, MAX_SANE_READING
import logging

class LevelingCalculatorError(Exception):
    """Custom exception for calculator errors."""
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors if errors is not None else []

class LevelingCalculator:
    def __init__(self, settings):
        logging.debug("LevelingCalculator.__init__ called")
        self.settings = settings

    def calculate_leveling(self, method, first_rl, last_rl_user, data):
        """Main calculation method that routes to specific calculation methods."""
        logging.debug(f"LevelingCalculator.calculate_leveling called: method={method}")
        
        reorganized_data, validation_errors = self.validate_input(data)
        if validation_errors:
            raise LevelingCalculatorError("Input validation failed", errors=validation_errors)
        
        if method == "HI":
            return self.calculate_hi(first_rl, last_rl_user, reorganized_data)
        elif method == "RF":
            return self.calculate_rise_and_fall(first_rl, last_rl_user, reorganized_data)
        else:
            raise LevelingCalculatorError(f"Unknown calculation method: {method}")

    def validate_input(self, data):
        """Validates the input data and returns reorganized data and errors."""
        logging.debug("LevelingCalculator.validate_input called")
        data_values, row_map = self._get_data_values(data)

        if not data_values:
            return None, [("info", "No data to calculate.")]

        error_msgs = []

        def add_error(msg, row_idx):
            error_msgs.append({"message": msg, "row": row_idx})

        # Validate first row
        first_row_error = self._validate_first_row(data_values, row_map)
        if first_row_error:
            add_error(first_row_error, row_map[0])

        # Validate each row's data and sequence
        for i, row in enumerate(data_values):
            row_idx = row_map[i]
            row_errors = self._validate_row_data(row, row_idx)
            for error in row_errors:
                add_error(error, row_idx)
            
            if i > 0:
                sequence_errors = self._validate_row_sequence(data_values[i-1], row, row_idx)
                for error in sequence_errors:
                    add_error(error, row_idx)

        # Validate last row
        last_row_error = self._validate_last_row(data_values, row_map)
        if last_row_error:
            add_error(last_row_error, row_map[-1])

        if error_msgs:
            return None, error_msgs

        return self._reorganize_data_for_calculation(data_values, row_map), []

    def _get_data_values(self, data):
        """Extracts non-empty data rows and their original indices."""
        logging.debug("LevelingCalculator._get_data_values called")
        data_values = []
        row_map = []
        for i, row_data in enumerate(data):
            # Expecting a list of strings
            row = [str(val).strip() for val in row_data]
            while len(row) < 5:
                row.append("")
            if any(row[1:]):
                data_values.append(row)
                row_map.append(i)
        return data_values, row_map

    def _validate_first_row(self, data_values, row_map):
        """Validates the first row of the survey data."""
        logging.debug("LevelingCalculator._validate_first_row called")
        # Unpack all 5 values, even if Design RL is not used in this specific validation
        _point, first_bs, first_is, first_fs, _design_rl = data_values[0] 
        if not first_bs or first_is or first_fs:
            return f"Row {row_map[0] + 1}: The first entry must be a Backsight (BS) only."
        return None

    def _validate_row_data(self, row, row_idx):
        """Validates the data within a single row."""
        logging.debug(f"LevelingCalculator._validate_row_data called: row_idx={row_idx}")
        # Unpack all 5 values
        point, bs, is_, fs, design_rl = row 
        errors = []
        for val, name in [(bs, "BS"), (is_, "IS"), (fs, "FS")]:
            if val:
                if not is_number(val):
                    errors.append(f"Row {row_idx + 1}: Invalid non-numeric value for {name}.")
                    continue
                num_val = float(val)
                if num_val < 0:
                    errors.append(f"Row {row_idx + 1}: {name} reading cannot be negative.")
                if num_val > MAX_SANE_READING:
                    errors.append(f"Row {row_idx + 1}: Warning - {name} reading ({val}) is unusually high.")
        
        if design_rl and not is_number(design_rl):
            errors.append(f"Row {row_idx + 1}: Invalid non-numeric value for Design RL.")

        if is_ and (bs or fs):
            errors.append(f"Row {row_idx + 1}: IS cannot be in the same row as BS or FS.")
        filled = [bool(bs), bool(is_), bool(fs)]
        if sum(filled) > 1 and not (bs and fs and not is_):
            errors.append(f"Row {row_idx + 1}: Invalid combination. Only BS and FS can be on the same line.")
        return errors

    def _validate_row_sequence(self, prev_row, current_row, row_idx):
        """Validates the logical sequence between two rows."""
        logging.debug(f"LevelingCalculator._validate_row_sequence called: prev_row_idx={row_idx-1}, current_row_idx={row_idx}")
        # Unpack all 5 values for both rows
        _prev_point, prev_bs, _prev_is, prev_fs, _prev_design_rl = prev_row
        _point, bs, is_, fs, _design_rl = current_row
        errors = []
        # A pure BS row cannot be followed by another pure BS row
        if prev_bs and not _prev_is and not prev_fs:
            if bs and not fs:
                errors.append(f"Row {row_idx + 1}: A BS cannot be followed by another BS unless it's a change point.")
        # A pure FS row must be followed by a BS (as part of a change point)
        if prev_fs and not prev_bs and not _prev_is:
            if not bs:
                errors.append(f"Row {row_idx + 1}: An FS must be followed by a BS on the next point.")
        return errors

    def _validate_last_row(self, data_values, row_map):
        """Validates the last row of the survey data."""
        logging.debug("LevelingCalculator._validate_last_row called")
        last_row_idx = row_map[-1]
        # Unpack all 5 values
        _point, last_bs, last_is, last_fs, _last_design_rl = data_values[-1]
        if last_is:
            return f"Row {last_row_idx + 1}: Last reading cannot be an IS. It must be an FS."
        if last_bs and not last_fs:
            return f"Row {last_row_idx + 1}: Last reading cannot be a BS. It must be an FS."
        return None

    def _reorganize_data_for_calculation(self, data_values, row_map):
        """Reorganizes data, auto-numbering points and marking change points with (cp)."""
        logging.debug("LevelingCalculator._reorganize_data_for_calculation called")
        reorganized = []
        station_counter = 1
        for i, row in enumerate(data_values):
            row_idx = row_map[i]
            point, bs, is_, fs, design_rl = row

            # Auto-number point if it's empty
            if not point.strip():
                point = str(station_counter)

            # If this row is a change point, append (cp) to the label
            if bs and fs:
                point_label = f"{point} (cp)"
            else:
                point_label = point

            reorganized.append((row_idx, [point_label, bs, is_, fs, design_rl]))
            station_counter += 1
        return reorganized

    def calculate_hi(self, first_rl, last_rl_user, reorganized_data):
        """Calculates using Height of Instrument method."""
        logging.debug("LevelingCalculator.calculate_hi called")
        
        results = []
        current_rl = first_rl
        hi = 0
        sum_bs = 0
        sum_fs = 0
        cp_count = bs_count = is_count = fs_count = 0
        
        for i, (row_idx, row_data) in enumerate(reorganized_data):
            point, bs_str, is_str, fs_str, design_rl_str = row_data
            design_rl_val = float(design_rl_str) if is_number(design_rl_str) else None

            if bs_str and fs_str:
                # Change point: process both FS and BS in one row
                fs_val = float(fs_str)
                bs_val = float(bs_str)
                sum_fs += fs_val
                sum_bs += bs_val
                fs_count += 1
                bs_count += 1
                # RL at change point (using HI from previous setup)
                rl_cp = hi - fs_val
                # New HI for next setup
                hi_new = rl_cp + bs_val
                # Add a single result row for the change point
                results.append({
                    "Point": point,
                    "BS": format_num(bs_val, self.settings["precision"]),
                    "FS": format_num(fs_val, self.settings["precision"]),
                    "HI": format_num(hi_new, self.settings["precision"]),
                    "RL": format_num(rl_cp, self.settings["precision"]),
                    "Design RL": format_num(design_rl_val, self.settings["precision"]) if design_rl_val is not None else ""
                })
                hi = hi_new
                current_rl = rl_cp
                cp_count += 1
            else:
                if bs_str:
                    bs_val = float(bs_str)
                    sum_bs += bs_val
                    bs_count += 1
                    hi = current_rl + bs_val
                    results.append({"Point": point, "BS": format_num(bs_val, self.settings["precision"]), "HI": format_num(hi, self.settings["precision"]), "RL": format_num(current_rl, self.settings["precision"]), "Design RL": format_num(design_rl_val, self.settings["precision"]) if design_rl_val is not None else ""})
                if is_str:
                    is_val = float(is_str)
                    is_count += 1
                    rl = hi - is_val
                    results.append({"Point": point, "IS": format_num(is_val, self.settings["precision"]), "HI": format_num(hi, self.settings["precision"]), "RL": format_num(rl, self.settings["precision"]), "Design RL": format_num(design_rl_val, self.settings["precision"]) if design_rl_val is not None else ""})
                if fs_str and not bs_str:
                    fs_val = float(fs_str)
                    sum_fs += fs_val
                    fs_count += 1
                    rl = hi - fs_val
                    results.append({"Point": point, "FS": format_num(fs_val, self.settings["precision"]), "HI": format_num(hi, self.settings["precision"]), "RL": format_num(rl, self.settings["precision"]), "Design RL": format_num(design_rl_val, self.settings["precision"]) if design_rl_val is not None else ""})
                    current_rl = rl
        
        if not results:
            return [], {}
        
        obtained_last_rl = float(results[-1]["RL"])
        adjustment_per_reading = 0
        if last_rl_user is not None:
            misclosure = obtained_last_rl - last_rl_user
            if len(results) > 1:
                adjustment_per_reading = -misclosure / (len(results) -1)
        
        total_adj = 0
        for i, res in enumerate(results):
            if i > 0:
                total_adj += adjustment_per_reading
            adjusted_rl = float(res["RL"]) + total_adj
            res["Adjustment"] = format_num(total_adj, self.settings["precision"])
            res["Adjusted RL"] = format_num(adjusted_rl, self.settings["precision"])
            res["Elevation"] = adjusted_rl  # Add Elevation key for the graph

            # Calculate Cut and Fill
            design_rl_for_point = float(res["Design RL"]) if is_number(res["Design RL"]) else None
            if design_rl_for_point is not None:
                diff = adjusted_rl - design_rl_for_point
                if diff > 0:
                    res["Fill"] = format_num(diff, self.settings["precision"])
                    res["Cut"] = ""
                elif diff < 0:
                    res["Cut"] = format_num(abs(diff), self.settings["precision"])
                    res["Fill"] = ""
                else:
                    res["Cut"] = ""
                    res["Fill"] = ""
            else:
                res["Cut"] = ""
                res["Fill"] = ""
        
        arith_check = sum_bs - sum_fs
        rl_diff = obtained_last_rl - first_rl
        arith_failed = abs(arith_check - rl_diff) > 10**(-self.settings["precision"])
        
        logging.info(f"HI Method Arithmetic Check:")
        logging.info(f"  Sum BS: {sum_bs}, Sum FS: {sum_fs}")
        logging.info(f"  Arith Check (Sum BS - Sum FS): {arith_check}")
        logging.info(f"  Last RL: {obtained_last_rl}, First RL: {first_rl}")
        logging.info(f"  RL Diff (Last RL - First RL): {rl_diff}")
        logging.info(f"  Check Failed: {arith_failed}")

        stats = {
            "cp": cp_count,
            "bs": bs_count,
            "is": is_count,
            "fs": fs_count,
            "sum_bs": sum_bs,
            "sum_fs": sum_fs,
            "arith_check": arith_check,
            "rl_diff": rl_diff,
            "arith_failed": arith_failed
        }
        
        return results, stats

    def calculate_rise_and_fall(self, first_rl, last_rl_user, reorganized_data):
        """Calculates using Rise & Fall method."""
        logging.debug("LevelingCalculator.calculate_rise_and_fall called")
        
        results = []
        current_rl = first_rl
        prev_reading = None
        sum_rise = sum_fall = 0
        cp_count = bs_count = is_count = fs_count = 0
        
        for i, (row_idx, row_data) in enumerate(reorganized_data):
            point, bs_str, is_str, fs_str, design_rl_str = row_data
            design_rl_val = float(design_rl_str) if is_number(design_rl_str) else None

            if bs_str and fs_str:
                # Process FS as the last reading of the previous setup
                rise = fall = ""
                if prev_reading is not None:
                    fs_val = float(fs_str)
                    diff = prev_reading - fs_val
                    if diff > 0:
                        rise = diff
                        sum_rise += rise
                        current_rl += rise
                    else:
                        fall = -diff
                        sum_fall += fall
                        current_rl -= fall
                    prev_reading = fs_val
                # Now process BS as the first reading of the new setup
                bs_val = float(bs_str)
                prev_reading = bs_val
                # Output a single row for the change point
                res_cp = {
                    "Point": point,
                    "BS": format_num(bs_val, self.settings["precision"]),
                    "FS": format_num(float(fs_str), self.settings["precision"]),
                    "RL": format_num(current_rl, self.settings["precision"]),
                    "Rise": format_num(rise, self.settings["precision"]) if rise else "",
                    "Fall": format_num(fall, self.settings["precision"]) if fall else "",
                    "Design RL": format_num(design_rl_val, self.settings["precision"]) if design_rl_val is not None else ""
                }
                bs_count += 1
                fs_count += 1
                cp_count += 1
                results.append(res_cp)
            else:
                readings = [(bs_str, "BS"), (is_str, "IS"), (fs_str, "FS")]
                filled = [(float(val), typ) for val, typ in readings if is_number(val)]
                if not filled:
                    continue
                value, typ = filled[0]
                rise = fall = ""
                if prev_reading is not None:
                    diff = prev_reading - value
                    if diff > 0:
                        rise = diff
                        sum_rise += rise
                        current_rl += rise
                    else:
                        fall = -diff
                        sum_fall += fall
                        current_rl -= fall
                res = {"Point": point, "RL": format_num(current_rl, self.settings["precision"]), "Rise": format_num(rise, self.settings["precision"]) if rise else "", "Fall": format_num(fall, self.settings["precision"]) if fall else "", "Design RL": format_num(design_rl_val, self.settings["precision"]) if design_rl_val is not None else ""}
                if typ == "BS":
                    bs_count += 1
                    res["BS"] = format_num(value, self.settings["precision"])
                    if prev_reading is not None:
                        cp_count += 1
                elif typ == "IS":
                    is_count += 1
                    res["IS"] = format_num(value, self.settings["precision"])
                elif typ == "FS":
                    fs_count += 1
                    res["FS"] = format_num(value, self.settings["precision"])
                results.append(res)
                prev_reading = value
        
        if not results:
            return [], {}
        
        obtained_last_rl = float(results[-1]["RL"])
        adjustment_per_reading = 0
        if last_rl_user is not None:
            misclosure = obtained_last_rl - last_rl_user
            if len(results) > 1:
                adjustment_per_reading = -misclosure / (len(results) - 1)
        
        total_adj = 0
        for i, res in enumerate(results):
            if i > 0:
                total_adj += adjustment_per_reading
            adjusted_rl = float(res["RL"]) + total_adj
            res["Adjustment"] = format_num(total_adj, self.settings["precision"])
            res["Adjusted RL"] = format_num(adjusted_rl, self.settings["precision"])
            res["Elevation"] = adjusted_rl

            design_rl_for_point = float(res["Design RL"]) if is_number(res["Design RL"]) else None
            if design_rl_for_point is not None:
                diff = adjusted_rl - design_rl_for_point
                if diff > 0:
                    res["Fill"] = format_num(diff, self.settings["precision"])
                    res["Cut"] = ""
                elif diff < 0:
                    res["Cut"] = format_num(abs(diff), self.settings["precision"])
                    res["Fill"] = ""
                else:
                    res["Cut"] = ""
                    res["Fill"] = ""
            else:
                res["Cut"] = ""
                res["Fill"] = ""
        
        arith_check = sum_rise - sum_fall
        rl_diff = obtained_last_rl - first_rl
        arith_failed = abs(arith_check - rl_diff) > 10**(-self.settings["precision"])

        logging.info(f"Rise and Fall Method Arithmetic Check:")
        logging.info(f"  Sum Rise: {sum_rise}, Sum Fall: {sum_fall}")
        logging.info(f"  Arith Check (Sum Rise - Sum Fall): {arith_check}")
        logging.info(f"  Last RL: {obtained_last_rl}, First RL: {first_rl}")
        logging.info(f"  RL Diff (Last RL - First RL): {rl_diff}")
        logging.info(f"  Check Failed: {arith_failed}")

        stats = {
            "cp": cp_count,
            "bs": bs_count,
            "is": is_count,
            "fs": fs_count,
            "sum_rise": sum_rise,
            "sum_fall": sum_fall,
            "arith_check": arith_check,
            "rl_diff": rl_diff,
            "arith_failed": arith_failed
        }
        
        return results, stats
