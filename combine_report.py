import os
import build_appendix

base_dir = "/Users/saidheerajreddypalle/Documents/AI_LOGISTICS"

# 1. Generate the appendix (which pulls all codebase and logs)
build_appendix.generate_appendix()

# 2. Combine the markdown files in order
files = [
    "ch1_intro.md",
    "ch2_analysis.md",
    "ch3_design.md",
    "ch4_implementation.md",
    "ch5_testing.md",
    "ch6_appendix.md"
]

output_file = os.path.join(base_dir, "Detailed_Project_Report.md")
with open(output_file, "w") as outfile:
    for fname in files:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r") as infile:
                outfile.write(infile.read())
                outfile.write("\n\n")
        else:
            print(f"Warning: {fpath} not found.")

print(f"Successfully compiled massive report into: {output_file}")
