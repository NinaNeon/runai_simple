# runai_simple
簡單常用的runai指令
## 步驟 3：建立 Environment

點 Assets → Environments → + NEW ENVIRONMENT，照 README 填：

- **Scope：** 選你的 project
- **Name：** `ken-wafercap`
- **Type：** 只勾 Workspace
- **Image：** `j3soon/runai-pytorch-mnist`
- **Pull policy：** Always pull
- **Tools：** Jupyter

**Command：**

```bash
/run.sh "pip install jupyterlab" "jupyter lab --ip=0.0.0.0 --no-browser --allow-root --NotebookApp.base_url=/${RUNAI_PROJECT}/${RUNAI_JOB_NAME} --NotebookApp.token='' --notebook-dir=/"
