// PasteMaster CI/CD pipeline.
//
// Jenkins CANNOT run on PythonAnywhere's free tier, so it runs elsewhere
// (your machine, Docker, or a VM). This pipeline builds + smoke-tests the
// backend, then triggers a deploy by calling the app's /api/deploy webhook,
// which git-pulls and reloads the app on PythonAnywhere.
//
// Prerequisites in Jenkins:
//   - A "Secret text" credential with ID 'pastemaster-deploy-token' holding
//     the same value as DEPLOY_TOKEN in the PythonAnywhere WSGI file.
//   - A Linux agent with python3 and curl (the default if you run Jenkins in
//     the official Docker image). For a Windows agent, swap `sh` for `bat`.

pipeline {
    agent any

    environment {
        BACKEND_URL  = 'https://htsingh200.pythonanywhere.com'
        DEPLOY_TOKEN = credentials('pastemaster-deploy-token')
    }

    options {
        timeout(time: 15, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        stage('Build') {
            steps {
                dir('backend') {
                    sh '''
                        python3 -m venv .ci-venv
                        . .ci-venv/bin/activate
                        pip install --quiet -r requirements.txt
                    '''
                }
            }
        }

        stage('Smoke test') {
            steps {
                dir('backend') {
                    // Boot the app factory: catches import errors, bad config,
                    // and broken blueprints before we ship.
                    sh '''
                        . .ci-venv/bin/activate
                        python -c "from app import create_app; create_app(); print('app boots OK')"
                    '''
                }
            }
        }

        stage('Deploy') {
            // Only auto-deploy the main line; adjust to your branch name.
            when { branch 'master' }
            steps {
                sh '''
                    echo "Triggering deploy on ${BACKEND_URL} ..."
                    curl --fail-with-body -sS -X POST "${BACKEND_URL}/api/deploy" \
                         -H "X-Deploy-Token: ${DEPLOY_TOKEN}"
                    echo ""
                    echo "Deploy request completed."
                '''
            }
        }
    }

    post {
        always  { sh 'rm -rf backend/.ci-venv || true' }
        success { echo 'Pipeline succeeded — app pulled and reloaded.' }
        failure { echo 'Pipeline failed — check the stage logs above.' }
    }
}
