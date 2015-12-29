from setuptools import setup, find_packages

try:
    import multiprocessing  # noqa
except ImportError:
    pass

setup(
    name="proxywall",
    version="1.0.0",
    packages=find_packages(),
    author="coding4m",
    author_email="coding4m@gmail.com",

    install_requires=['python-etcd>=0.4.3', 'docker-py>=1.6.0', 'jsonselect>=0.2.3', 'jinja2>=2.8'],

    entry_points={
        'console_scripts': [
            'proxywall-daemon = proxywall.daemon:main',
            'proxywall-agent = proxywall.agent:main',
            'proxywall-client = proxywall.client:main'
        ]
    }

)
