# Run Raw Directions with Email Notebook 
DATE=`date +%m-%d-%y-%H`
NOTEBOOK_PATH=/home/malcolm/WorkTransit/RunDrivingAnalysis.ipynb
RUN_NB_PATH=/home/malcolm/WorkTransit/run_notebooks/RunDrivingAnalysis_${DATE}.ipynb

source ~/main/bin/activate
papermill $NOTEBOOK_PATH $RUN_NB_PATH

export papermill_exit_status=$?
if [ $papermill_exit_status -eq 0 ]
then
  echo "removing "$RUN_NB_PATH
  rm $RUN_NB_PATH
fi

# 10 11 * * Sun bash /home/malcolm/WorkTransit/scripts/run_driving_analysis.sh > /home/malcolm/Logs/driving_analysis.log 2>&1