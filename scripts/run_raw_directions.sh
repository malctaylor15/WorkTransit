# Run Raw Directions with Email Notebook 
DATE=`date +%m-%d-%y-%H`
NOTEBOOK_PATH=/home/malcolm/WorkTransit/Run_RawDirections.ipynb
RUN_NB_PATH=/home/malcolm/WorkTransit/run_notebooks/Run_RawDirections_${DATE}.ipynb

source ~/main/bin/activate
papermill $NOTEBOOK_PATH $RUN_NB_PATH

export papermill_exit_status=$?
if [ $papermill_exit_status -eq 0 ]
then
  echo "removing "$RUN_NB_PATH
  rm $RUN_NB_PATH
fi

# 0,15,30,45 7,8,9,17,18,19 * * * bash /home/malcolm/WorkTransit/scripts/run_raw_directions.sh > /home/malcolm/Logs/raw_directions.log 2>&1