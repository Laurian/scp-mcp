# Environment Configuration

This project uses a layered environment configuration system for flexibility and security.

## File Structure

- `.env.template` - Base configuration template (committed to git)
- `.env.example` - Example with documentation (committed to git) 
- `.env.local` - Your personal local settings (gitignored)
- `.env.local.example` - Template for local settings (gitignored)

## Quick Setup

### Option 1: Using Make (Recommended)
```bash
make setup-env
```

### Option 2: Manual Setup
```bash
cp .env.template .env.local
```

After setup, edit `.env.local` with your personal settings:
- Add your HuggingFace token
- Set API keys for AI services  
- Customize paths and performance settings

## Key Configuration

### HuggingFace Models
The default model cache location is `./models` directory:
```env
HUGGINGFACE_HUB_CACHE=./models
TRANSFORMERS_CACHE=./models
HF_HOME=./models
```

### Database
LanceDB storage location:
```env
LANCEDB_URI=./data/lancedb
```

### API Keys
Set these in your `.env.local` file:
```env
HF_TOKEN=hf_your_token_here
OPENAI_API_KEY=sk-your_key_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

## Loading Priority

1. `.env.template` (base defaults)
2. `.env.local` (your overrides)

Never commit `.env.local` or any file containing real API keys!

## Available Make Targets

Run `make help` to see all available targets, including:
- `make setup-env` - Set up environment configuration
- `make data` - Ensure SCP data is available
- `make download` - Download fresh SCP data
- `make clean-data` - Remove downloaded data
