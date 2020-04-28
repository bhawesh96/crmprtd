@Library('pcic-pipeline-library')_


node {
    stage('Code Collection') {
        collectCode()
    }

    stage('Testing') {
        def requirements = ['requirements.txt', 'test_requirements.txt']
        def pytestArgs = '-v --tb=short --cov --flake8'
        def options = [containerData: 'crmprtd']

        parallel "Python 3.6": {
            runPythonTestSuite('pcic/test-env:python3.6', requirements, pytestArgs, options)
        },
        "Python 3.7": {
            runPythonTestSuite('pcic/test-env:python3.7', requirements, pytestArgs, options)
        }
    }

    if (isPypiPublishable()) {
        stage('Push to PYPI') {
            publishPythonPackage('pcic/test-env:python3.6', 'PCIC_PYPI_CREDS')
        }
    }

    stage('Clean Workspace') {
        cleanWs()
    }
}