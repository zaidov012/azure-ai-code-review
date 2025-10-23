"""
Quick validation script to test configuration setup.
Run this after installing dependencies to verify everything is working.
"""

from src.config import load_config, load_config_from_env
import sys
import os


def test_config_file():
    """Test loading from config.yaml file."""
    print("\n" + "=" * 60)
    print("Testing Configuration from config.yaml")
    print("=" * 60)
    
    config_path = "config.yaml"
    
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        print("   Please copy config.example.yaml to config.yaml and fill in your values")
        return False
    
    try:
        config = load_config(config_path)
        print("✅ Configuration loaded successfully!")
        print(f"\nLLM Configuration:")
        print(f"  Provider: {config.llm.provider.value}")
        print(f"  Model: {config.llm.model}")
        print(f"  Temperature: {config.llm.temperature}")
        print(f"  Max Tokens: {config.llm.max_tokens}")
        
        print(f"\nAzure DevOps Configuration:")
        print(f"  Organization: {config.azure_devops.organization_url}")
        print(f"  Project: {config.azure_devops.project}")
        print(f"  Repository: {config.azure_devops.repository}")
        print(f"  Verify SSL: {config.azure_devops.verify_ssl}")
        
        print(f"\nReview Configuration:")
        print(f"  Review Scope: {', '.join(config.review.review_scope)}")
        print(f"  Comment Style: {config.review.comment_style}")
        print(f"  Max Files: {config.review.max_files_per_review}")
        
        print(f"\nLog Level: {config.log_level}")
        
        errors = config.validate()
        if errors:
            print("\n❌ Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("\n✅ Configuration is valid!")
            return True
            
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return False
    except ValueError as e:
        print(f"❌ Validation Error:\n{e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False


def test_env_config():
    """Test loading from environment variables."""
    print("\n" + "=" * 60)
    print("Testing Configuration from Environment Variables")
    print("=" * 60)
    
    required_vars = [
        "LLM_PROVIDER",
        "LLM_MODEL",
        "AZDO_ORG_URL",
        "AZDO_PROJECT",
        "AZDO_REPOSITORY",
    ]
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Skipping environment variable test")
        return None
    
    try:
        config = load_config_from_env()
        print("✅ Configuration loaded from environment variables!")
        print(f"  Provider: {config.llm.provider.value}")
        print(f"  Model: {config.llm.model}")
        print(f"  Project: {config.azure_devops.project}")
        
        errors = config.validate()
        if errors:
            print("\n❌ Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("✅ Environment configuration is valid!")
            return True
            
    except ValueError as e:
        print(f"❌ Validation Error:\n{e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("Azure DevOps AI PR Review - Configuration Validation")
    print("=" * 60)
    
    file_result = test_config_file()
    env_result = test_env_config()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if file_result:
        print("✅ Config file validation: PASSED")
    elif file_result is False:
        print("❌ Config file validation: FAILED")
    else:
        print("⚠️  Config file validation: SKIPPED")
    
    if env_result:
        print("✅ Environment variables validation: PASSED")
    elif env_result is False:
        print("❌ Environment variables validation: FAILED")
    else:
        print("⚠️  Environment variables validation: SKIPPED")
    
    if file_result or env_result:
        print("\n✅ At least one configuration method is working!")
        print("\n🎉 Stage 1 Complete! Ready to proceed to Stage 2.")
        return 0
    else:
        print("\n❌ No valid configuration found.")
        print("\nPlease either:")
        print("  1. Copy config.example.yaml to config.yaml and fill in your values")
        print("  2. Set the required environment variables (see .env.example)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
