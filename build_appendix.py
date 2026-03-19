import os
import glob

def generate_appendix():
    base_dir = "/Users/saidheerajreddypalle/Documents/AI_LOGISTICS"
    output_file = os.path.join(base_dir, "ch6_appendix.md")
    
    with open(output_file, "w") as f:
        f.write("# Chapter 6: Appendices\n\n")
        f.write("## Appendix A: Core Application Source Code\n\n")
        f.write("The following sections contain the critical source code making up the rule-based logic, state machine, and service layers of the AI Logistics application. These components replaced the third-party LLM dependencies, acting as the brain of the local operation.\n\n")
        
        # Files to include to build up page count with real project data
        target_files = [
            "app/ai/agent.py",
            "app/ai/state_machine.py",
            "app/ai/mock_ai_parser.py",
            "app/services/location_resolver.py",
            "app/services/pricing_service.py",
            "app/services/booking_service.py",
            "app/api/routes/webhook.py",
            "app/models/booking.py",
            "app/utils/simulation.py",
            "test_resilience.sh"
        ]
        
        for file_path in target_files:
            full_path = os.path.join(base_dir, file_path)
            if os.path.exists(full_path):
                f.write(f"### {os.path.basename(file_path)}\n\n")
                f.write(f"**Path: `{file_path}`**\n\n")
                if file_path.endswith('.sh'):
                    f.write("```bash\n")
                else:
                    f.write("```python\n")
                
                with open(full_path, "r") as src:
                    f.write(src.read())
                    
                f.write("\n```\n\n")
                
        # Add test logs
        f.write("## Appendix B: Automated Resilience QA Logs\n\n")
        f.write("The following log represents the output of the automated chaos and resilience bash suite (`test_resilience.sh`) verifying fault tolerance and error boundaries.\n\n")
        
        # We will run the test resilience script and capture its output to append here in the bash script later, or just run it via Python.
        import subprocess
        f.write("```text\n")
        try:
            result = subprocess.run(["bash", os.path.join(base_dir, "test_resilience.sh")], capture_output=True, text=True, cwd=base_dir)
            f.write(result.stdout)
        except Exception as e:
            f.write(f"Error capturing test logs: {e}")
        f.write("\n```\n\n")
        
    print(f"Generated Appendix at {output_file}")

if __name__ == "__main__":
    generate_appendix()
