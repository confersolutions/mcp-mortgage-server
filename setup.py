from setuptools import setup, find_packages

# Read version from server.py
with open('server.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip('"').strip("'")
            break

# Read README for long description
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mcp-mortgage-server',
    version=version,
    author='Confer Solutions',
    author_email='info@confersolutions.ai',
    description='Mortgage Comparison Platform API Server',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/confersolutions/mcp-mortgage-server',
    project_urls={
        'Homepage': 'https://confersolutions.ai',
        'Source': 'https://github.com/confersolutions/mcp-mortgage-server',
        'Issues': 'https://github.com/confersolutions/mcp-mortgage-server/issues',
    },
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Office/Business :: Financial :: Mortgage',
    ],
    python_requires='>=3.8',
    install_requires=[
        'fastapi>=0.109.0',
        'uvicorn>=0.27.0',
        'slowapi>=0.1.9',
        'python-dotenv>=1.0.0',
        'pydantic>=2.0.0',
        'nest-asyncio>=1.6.0'
    ],
    extras_require={
        'all': [
            'crewai>=0.19.0',
            'ag2>=0.7.5',
            'langchain>=0.1.0',
            'langchain-openai>=0.0.5'
        ]
    }
) 