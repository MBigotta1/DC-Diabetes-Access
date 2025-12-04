import pandas as pd
import os
from tabulate import tabulate
from typing import Dict, List, Tuple
import warnings

warnings.filterwarnings('ignore')

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEDICINES_FILE = os.path.join(SCRIPT_DIR, 'medicines.csv')
INSURANCE_FILE = os.path.join(SCRIPT_DIR, 'insurance.csv')
COVERAGE_FILE = os.path.join(SCRIPT_DIR, 'insurance_medicine_coverage.csv')


class DiabetesCostComparator:
    """
    A class to help users compare diabetes medications and insurance plans
    based on cost, effectiveness, and coverage.
    """
    
    def __init__(self):
        """Initialize the comparator by loading CSV data."""
        try:
            self.medicines_df = pd.read_csv(MEDICINES_FILE)
            self.insurance_df = pd.read_csv(INSURANCE_FILE)
            self.coverage_df = pd.read_csv(COVERAGE_FILE)
            
            # Convert numeric columns
            numeric_cols_med = ['effectiveness_rating', 'average_cost_per_month', 'goodrx_price']
            for col in numeric_cols_med:
                if col in self.medicines_df.columns:
                    self.medicines_df[col] = pd.to_numeric(self.medicines_df[col], errors='coerce')
            
            numeric_cols_ins = ['copay_primary_care', 'copay_specialist', 'copay_emergency', 
                               'deductible', 'annual_max_copay', 'coverage_percentage']
            for col in numeric_cols_ins:
                if col in self.insurance_df.columns:
                    self.insurance_df[col] = pd.to_numeric(self.insurance_df[col], errors='coerce')
            
            numeric_cols_cov = ['copay_amount']
            for col in numeric_cols_cov:
                if col in self.coverage_df.columns:
                    self.coverage_df[col] = pd.to_numeric(self.coverage_df[col], errors='coerce')
            
            print("✓ Data loaded successfully!\n")
        except FileNotFoundError as e:
            print(f"Error: Could not find required CSV file: {e}")
            print(f"Please ensure the following files exist in {SCRIPT_DIR}:")
            print("  - medicines.csv")
            print("  - insurance.csv")
            print("  - insurance_medicine_coverage.csv")
            exit(1)
    
    def get_user_selections(self) -> Tuple[str, str]:
        """
        Get the user's current medicine and insurance selections.
        
        Returns:
            Tuple of (medicine_name, insurance_name)
        """
        print("=" * 60)
        print("DIABETES MEDICINE & INSURANCE COMPARISON TOOL")
        print("=" * 60)
        print()

        # Let user choose whether to pick medicine first or insurance first
        while True:
            order_choice = input("Choose selection order: 1) Medicine first  2) Insurance first (enter 1 or 2): ").strip()
            if order_choice in ("1", "2"):
                break
            print("Invalid choice. Please enter 1 or 2.")

        selected_medicine = None
        selected_insurance = None

        if order_choice == "1":
            # Medicine first
            print("Available Diabetes Medicines:")
            print("-" * 60)
            medicines = self.medicines_df['medicine_name'].unique().tolist()
            for i, med in enumerate(medicines, 1):
                print(f"{i}. {med}")
            print()

            while True:
                try:
                    med_choice = int(input("Enter the number of your current medicine: "))
                    if 1 <= med_choice <= len(medicines):
                        selected_medicine = medicines[med_choice - 1]
                        break
                    else:
                        print("Invalid choice. Please enter a valid number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            print()

            # Show insurances annotated with coverage for the selected medicine
            print("Available Insurance Plans (shows if they cover the selected medicine):")
            print("-" * 60)
            insurances = self.insurance_df['insurance_name'].unique().tolist()
            for i, ins in enumerate(insurances, 1):
                cov = self.get_coverage_info(ins, selected_medicine)
                covered = "Yes" if cov and cov.get('covered') == 'Yes' else "No"
                print(f"{i}. {ins}  (Covers: {covered})")
            print()

            while True:
                try:
                    ins_choice = int(input("Enter the number of your insurance plan: "))
                    if 1 <= ins_choice <= len(insurances):
                        selected_insurance = insurances[ins_choice - 1]
                        break
                    else:
                        print("Invalid choice. Please enter a valid number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

        else:
            # Insurance first
            print("Available Insurance Plans:")
            print("-" * 60)
            insurances = self.insurance_df['insurance_name'].unique().tolist()
            for i, ins in enumerate(insurances, 1):
                print(f"{i}. {ins}")
            print()

            while True:
                try:
                    ins_choice = int(input("Enter the number of your insurance plan: "))
                    if 1 <= ins_choice <= len(insurances):
                        selected_insurance = insurances[ins_choice - 1]
                        break
                    else:
                        print("Invalid choice. Please enter a valid number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            print()

            # Show medicines annotated with coverage for the selected insurance
            print("Available Diabetes Medicines (shows if selected insurance covers them):")
            print("-" * 60)
            medicines = self.medicines_df['medicine_name'].unique().tolist()
            for i, med in enumerate(medicines, 1):
                cov = self.get_coverage_info(selected_insurance, med)
                covered = "Yes" if cov and cov.get('covered') == 'Yes' else "No"
                print(f"{i}. {med}  (Covered: {covered})")
            print()

            while True:
                try:
                    med_choice = int(input("Enter the number of your current medicine: "))
                    if 1 <= med_choice <= len(medicines):
                        selected_medicine = medicines[med_choice - 1]
                        break
                    else:
                        print("Invalid choice. Please enter a valid number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

        return selected_medicine, selected_insurance
    
    def get_medicine_info(self, medicine_name: str) -> Dict:
        """Get detailed information about a specific medicine."""
        med_info = self.medicines_df[self.medicines_df['medicine_name'] == medicine_name]
        if med_info.empty:
            return None
        return med_info.iloc[0].to_dict()
    
    def get_insurance_info(self, insurance_name: str) -> Dict:
        """Get detailed information about a specific insurance plan."""
        ins_info = self.insurance_df[self.insurance_df['insurance_name'] == insurance_name]
        if ins_info.empty:
            return None
        return ins_info.iloc[0].to_dict()
    
    def get_coverage_info(self, insurance_name: str, medicine_name: str) -> Dict:
        """Get coverage information for a specific insurance-medicine combination."""
        coverage = self.coverage_df[
            (self.coverage_df['insurance_name'] == insurance_name) &
            (self.coverage_df['medicine_name'] == medicine_name)
        ]
        if coverage.empty:
            return None
        return coverage.iloc[0].to_dict()
    
    def calculate_total_cost(self, medicine_info: Dict, insurance_info: Dict, 
                            coverage_info: Dict, months: int = 12) -> float:
        """
        Calculate total annual cost for a medicine under a specific insurance plan.
        
        Args:
            medicine_info: Dictionary with medicine details
            insurance_info: Dictionary with insurance details
            coverage_info: Dictionary with coverage details
            months: Number of months to calculate for (default: 12)
        
        Returns:
            Total annual cost
        """
        # Treat coverage_info as valid only when it explicitly says the medicine is covered.
        covered_flag = False
        try:
            if coverage_info is not None:
                covered_flag = str(coverage_info.get('covered')).strip().lower() == 'yes'
        except Exception:
            covered_flag = False

        if not covered_flag:
            # If we don't have coverage info:
            # - if no insurance context provided (we're showing GoodRx / cash price), prefer goodrx_price when available
            try:
                # insurance_info may be None when we want to show GoodRx/cash pricing
                if insurance_info is None:
                    gr = medicine_info.get('goodrx_price')
                    if gr is not None and not pd.isna(gr):
                        return float(gr) * months
            except Exception:
                pass

            # Fallback: use average monthly price
            return medicine_info.get('average_cost_per_month', 0) * months
        # At this point coverage_info exists and indicates coverage.
        copay = coverage_info.get('copay_amount')
        try:
            copay = float(copay)
        except Exception:
            copay = 0.0

        deductible = 0.0
        try:
            if insurance_info and insurance_info.get('deductible') is not None:
                deductible = float(insurance_info.get('deductible'))
        except Exception:
            deductible = 0.0

        # Calculate total cost (deductible + copays)
        total_copays = copay * months
        total_cost = deductible + total_copays

        return total_cost
    
    def display_current_selection(self, medicine: str, insurance: str):
        """Display detailed information about the user's current selections."""
        print("\n" + "=" * 60)
        print("YOUR CURRENT SELECTION DETAILS")
        print("=" * 60)
        
        med_info = self.get_medicine_info(medicine)
        ins_info = self.get_insurance_info(insurance)
        cov_info = self.get_coverage_info(insurance, medicine)
        
        # Medicine details
        print(f"\n📋 MEDICINE: {medicine}")
        print("-" * 60)
        med_table = [
            ["Type", med_info['type']],
            ["Effectiveness Rating", f"{med_info['effectiveness_rating']}/10"],
            ["Possible Side Effects", med_info['side_effects']],
            ["Average Monthly Cost", f"${med_info['average_cost_per_month']:.2f}"]
        ]
        print(tabulate(med_table, tablefmt="grid"))
        
        # Insurance details
        print(f"\n🛡️  INSURANCE: {insurance}")
        print("-" * 60)
        ins_table = [
            ["Provider", ins_info['provider']],
            ["Primary Care Copay", f"${ins_info['copay_primary_care']:.2f}"],
            ["Specialist Copay", f"${ins_info['copay_specialist']:.2f}"],
            ["Emergency Copay", f"${ins_info['copay_emergency']:.2f}"],
            ["Deductible", f"${ins_info['deductible']:.2f}"],
            ["Annual Max Copay", f"${ins_info['annual_max_copay']:.2f}"],
            ["Coverage Percentage", f"{ins_info['coverage_percentage']}%"]
        ]
        print(tabulate(ins_table, tablefmt="grid"))
        
        # Coverage information
        print(f"\n💊 COVERAGE FOR {medicine.upper()}")
        print("-" * 60)
        if cov_info:
            cov_table = [
                ["Covered", "Yes" if cov_info['covered'] == 'Yes' else "No"],
                ["Copay Amount", f"${cov_info['copay_amount']:.2f}"],
                ["Tier Level", cov_info['tier_level']]
            ]
        else:
            cov_table = [
                ["Covered", "Not specifically listed (likely not covered)"],
                ["Copay Amount", "Full Cost"],
                ["Tier Level", "Not covered"]
            ]
        print(tabulate(cov_table, tablefmt="grid"))
        
        # Calculate costs
        annual_cost = self.calculate_total_cost(dict(med_info), dict(ins_info), cov_info, 12)
        print(f"\n💰 ESTIMATED ANNUAL COST: ${annual_cost:.2f}")
        print(f"   Monthly Average: ${annual_cost / 12:.2f}")
    
    def compare_medicines(self, insurance_name: str, exclude_medicine: str = None):
        """Compare all medicines under a specific insurance plan."""
        print("\n" + "=" * 60)
        print(f"MEDICINE COMPARISON (for {insurance_name})")
        print("=" * 60 + "\n")
        
        ins_info = self.get_insurance_info(insurance_name)
        comparison_data = []
        
        for _, medicine in self.medicines_df.iterrows():
            med_name = medicine['medicine_name']
            
            if exclude_medicine and med_name == exclude_medicine:
                continue
            
            cov_info = self.get_coverage_info(insurance_name, med_name)
            annual_cost = self.calculate_total_cost(
                dict(medicine), 
                dict(ins_info), 
                cov_info, 
                12
            )
            
            comparison_data.append([
                med_name,
                f"{medicine['type']}",
                f"{medicine['effectiveness_rating']}/10",
                f"${medicine['average_cost_per_month']:.2f}",
                f"${annual_cost:.2f}",
                medicine['side_effects']
            ])
        
        # Sort by annual cost
        comparison_data.sort(key=lambda x: float(x[4].replace('$', '')))
        
        headers = ["Medicine", "Type", "Effectiveness", "Base Cost/Mo", "Annual Cost", "Side Effects"]
        print(tabulate(comparison_data, headers=headers, tablefmt="grid"))
    
    def compare_insurance_plans(self, medicine_name: str, exclude_insurance: str = None):
        """Compare all insurance plans for a specific medicine."""
        print("\n" + "=" * 60)
        print(f"INSURANCE COMPARISON (for {medicine_name})")
        print("=" * 60 + "\n")
        
        med_info = self.get_medicine_info(medicine_name)
        comparison_data = []
        
        for _, insurance in self.insurance_df.iterrows():
            ins_name = insurance['insurance_name']
            
            if exclude_insurance and ins_name == exclude_insurance:
                continue
            
            cov_info = self.get_coverage_info(ins_name, medicine_name)
            annual_cost = self.calculate_total_cost(
                dict(med_info),
                dict(insurance),
                cov_info,
                12
            )
            
            comparison_data.append([
                ins_name,
                f"${insurance['copay_primary_care']:.2f}",
                f"${insurance['deductible']:.2f}",
                f"{insurance['coverage_percentage']}%",
                f"${annual_cost:.2f}",
                "Yes" if cov_info and cov_info['covered'] == 'Yes' else "No"
            ])
        
        # Sort by annual cost
        comparison_data.sort(key=lambda x: float(x[4].replace('$', '')))
        
        headers = ["Insurance", "Primary Care Copay", "Deductible", "Coverage %", "Annual Cost", "Covers Med"]
        print(tabulate(comparison_data, headers=headers, tablefmt="grid"))
    
    def get_recommendations(self, current_medicine: str, current_insurance: str):
        """Provide recommendations for alternative medicines or insurance plans."""
        print("\n" + "=" * 60)
        print("RECOMMENDATIONS")
        print("=" * 60 + "\n")
        
        med_info = self.get_medicine_info(current_medicine)
        ins_info = self.get_insurance_info(current_insurance)
        current_cost = self.calculate_total_cost(
            med_info,
            ins_info,
            self.get_coverage_info(current_insurance, current_medicine),
            12
        )
        
        print(f"Your current annual cost: ${current_cost:.2f}\n")
        
        # Find cheaper medicines with comparable effectiveness
        print("💊 ALTERNATIVE MEDICINES (with comparable effectiveness):")
        print("-" * 60)
        
        alt_medicines = []
        for _, medicine in self.medicines_df.iterrows():
            if medicine['medicine_name'] == current_medicine:
                continue
            
            if medicine['effectiveness_rating'] >= (med_info['effectiveness_rating'] - 1):
                cov_info = self.get_coverage_info(current_insurance, medicine['medicine_name'])
                alt_cost = self.calculate_total_cost(
                    dict(medicine),
                    dict(ins_info),
                    cov_info,
                    12
                )
                
                savings = current_cost - alt_cost
                alt_medicines.append((medicine['medicine_name'], alt_cost, savings))
        
        if alt_medicines:
            alt_medicines.sort(key=lambda x: x[2], reverse=True)
            for med, cost, savings in alt_medicines[:5]:
                if savings > 0:
                    print(f"  • {med}: ${cost:.2f}/year (save ${savings:.2f} annually)")
                else:
                    print(f"  • {med}: ${cost:.2f}/year (costs ${abs(savings):.2f} more)")
        else:
            print("  No comparable alternatives found.")
        
        # Find cheaper insurance plans
        print("\n🛡️  ALTERNATIVE INSURANCE PLANS:")
        print("-" * 60)
        
        alt_insurance = []
        for _, insurance in self.insurance_df.iterrows():
            if insurance['insurance_name'] == current_insurance:
                continue
            
            cov_info = self.get_coverage_info(insurance['insurance_name'], current_medicine)
            alt_cost = self.calculate_total_cost(
                dict(med_info),
                dict(insurance),
                cov_info,
                12
            )
            
            savings = current_cost - alt_cost
            alt_insurance.append((insurance['insurance_name'], alt_cost, savings))
        
        if alt_insurance:
            alt_insurance.sort(key=lambda x: x[2], reverse=True)
            for ins, cost, savings in alt_insurance[:5]:
                if savings > 0:
                    print(f"  • {ins}: ${cost:.2f}/year (save ${savings:.2f} annually)")
                else:
                    print(f"  • {ins}: ${cost:.2f}/year (costs ${abs(savings):.2f} more)")
        else:
            print("  No cheaper plans available.")
    
    def run(self):
        """Main application loop."""
        try:
            # Get user selections
            medicine, insurance = self.get_user_selections()
            
            # Display current selection details
            self.display_current_selection(medicine, insurance)
            
            # Show comparisons
            print("\n")
            self.compare_medicines(insurance, exclude_medicine=medicine)
            
            print("\n")
            self.compare_insurance_plans(medicine, exclude_insurance=insurance)
            
            # Get recommendations
            self.get_recommendations(medicine, insurance)
            
            # Ask if user wants to explore other options
            print("\n" + "=" * 60)
            print("EXPLORE OTHER OPTIONS")
            print("=" * 60)
            
            while True:
                print("\nWhat would you like to do?")
                print("1. Compare a different medicine")
                print("2. Compare a different insurance plan")
                print("3. Exit")
                
                choice = input("\nEnter your choice (1-3): ").strip()
                
                if choice == "1":
                    med_list = self.medicines_df['medicine_name'].unique().tolist()
                    print("\nAvailable medicines:")
                    for i, m in enumerate(med_list, 1):
                        print(f"{i}. {m}")
                    
                    try:
                        med_choice = int(input("Enter medicine number: "))
                        if 1 <= med_choice <= len(med_list):
                            medicine = med_list[med_choice - 1]
                            self.display_current_selection(medicine, insurance)
                            self.compare_medicines(insurance, exclude_medicine=medicine)
                            self.get_recommendations(medicine, insurance)
                        else:
                            print("Invalid choice.")
                    except ValueError:
                        print("Invalid input.")
                
                elif choice == "2":
                    ins_list = self.insurance_df['insurance_name'].unique().tolist()
                    print("\nAvailable insurance plans:")
                    for i, ins in enumerate(ins_list, 1):
                        print(f"{i}. {ins}")
                    
                    try:
                        ins_choice = int(input("Enter insurance number: "))
                        if 1 <= ins_choice <= len(ins_list):
                            insurance = ins_list[ins_choice - 1]
                            self.display_current_selection(medicine, insurance)
                            self.compare_insurance_plans(medicine, exclude_insurance=insurance)
                            self.get_recommendations(medicine, insurance)
                        else:
                            print("Invalid choice.")
                    except ValueError:
                        print("Invalid input.")
                
                elif choice == "3":
                    print("\nThank you for using the Diabetes Medicine & Insurance Comparison Tool!")
                    break
                
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
        
        except KeyboardInterrupt:
            print("\n\nApplication terminated by user.")
        except Exception as e:
            print(f"\nAn error occurred: {e}")


def main():
    """Entry point for the application."""
    app = DiabetesCostComparator()
    app.run()


if __name__ == "__main__":
    main()
