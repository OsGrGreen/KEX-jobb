from typing import Optional, List

import pandas as pd
from pynwb import NWBFile

from allensdk.brain_observatory.behavior.behavior_session import \
    BehaviorSession
from allensdk.brain_observatory.behavior.data_files import SyncFile, \
    BehaviorStimulusFile, MappingStimulusFile, ReplayStimulusFile
from allensdk.brain_observatory.behavior.data_objects import StimulusTimestamps
from allensdk.brain_observatory.ecephys._behavior_ecephys_metadata import \
    BehaviorEcephysMetadata
from allensdk.brain_observatory.ecephys.optotagging import OptotaggingTable
from allensdk.brain_observatory.ecephys.probes import Probes


class BehaviorEcephysSession(BehaviorSession):
    """
    Represents a session with behavior + ecephys
    """
    def __init__(
            self,
            behavior_session: BehaviorSession,
            metadata: BehaviorEcephysMetadata,
            probes: Probes,
            optotagging_table: OptotaggingTable
    ):
        super().__init__(
            behavior_session_id=behavior_session._behavior_session_id,
            date_of_acquisition=behavior_session._date_of_acquisition,
            licks=behavior_session._licks,
            metadata=metadata,
            raw_running_speed=behavior_session._raw_running_speed,
            rewards=behavior_session._rewards,
            running_speed=behavior_session._running_speed,
            running_acquisition=behavior_session._running_acquisition,
            stimuli=behavior_session._stimuli,
            stimulus_timestamps=behavior_session._stimulus_timestamps,
            task_parameters=behavior_session._task_parameters,
            trials=behavior_session._trials
        )
        self._probes = probes
        self._optotagging_table = optotagging_table

    @property
    def probes(self) -> pd.DataFrame:
        """
        Returns
        -------
        A dataframe with columns
            - id: probe id
            - description: probe name
            - location: probe location
            - lfp_sampling_rate: LFP sampling rate
            - has_lfp_data: Whether this probe has LFP data
        """
        return self._probes.to_dataframe()

    @property
    def optotagging_table(self) -> pd.DataFrame:
        """

        Returns
        -------
        A dataframe with columns
            - start_time: onset of stimulation
            - condition: optical stimulation pattern
            - level: intensity (in volts output to the LED) of stimulation
            - stop_time: stop time of stimulation
            - stimulus_name: stimulus name
            - duration: duration of stimulation
        """
        return self._optotagging_table.value

    @property
    def metadata(self) -> dict:
        behavior_meta = super()._get_metadata(
            behavior_metadata=self._metadata)
        ecephys_meta = {
            'ecephys_session_id': self._metadata.ecephys_session_id
        }
        return {
            **behavior_meta,
            **ecephys_meta
        }

    @classmethod
    def from_json(
            cls,
            session_data: dict,
            stimulus_timestamps: Optional[StimulusTimestamps] = None,
            stimulus_presentation_exclude_columns: Optional[List[str]] = None
    ) -> "BehaviorEcephysSession":
        """

        Parameters
        ----------
        session_data: Dict of input data necessary to construct a session
        stimulus_timestamps: Optional `StimulusTimestamps`
        stimulus_presentation_exclude_columns:  Optional list of columns to
            exclude from stimulus presentations table

        Returns
        -------
        Instantiated `BehaviorEcephysSession`
        """
        probes = session_data['probes']
        session_data = session_data['session_data']

        monitor_delay = cls._get_monitor_delay() \
            if 'monitor_delay' not in session_data \
            else session_data['monitor_delay']

        if stimulus_timestamps is None:
            stimulus_timestamps = StimulusTimestamps\
                .from_multiple_stimulus_blocks(
                    sync_file=SyncFile.from_json(dict_repr=session_data,
                                                 permissive=True),
                    list_of_stims=[
                        BehaviorStimulusFile.from_json(dict_repr=session_data),
                        MappingStimulusFile.from_json(dict_repr=session_data),
                        ReplayStimulusFile.from_json(dict_repr=session_data)
                    ],
                    monitor_delay=monitor_delay
                )

        behavior_session = BehaviorSession.from_json(
            session_data=session_data,
            stimulus_timestamps=stimulus_timestamps,
            read_stimulus_presentations_table_from_file=True,
            stimulus_presentation_exclude_columns=
            stimulus_presentation_exclude_columns
        )
        probes = Probes.from_json(probes=probes)
        optotagging_table = OptotaggingTable.from_json(dict_repr=session_data)

        return BehaviorEcephysSession(
            behavior_session=behavior_session,
            probes=probes,
            optotagging_table=optotagging_table,
            metadata=BehaviorEcephysMetadata.from_json(dict_repr=session_data)
        )

    def to_nwb(self) -> NWBFile:
        nwbfile = super().to_nwb(
            add_metadata=False,
            include_experiment_description=False,
            stimulus_presentations_stimulus_column_name='stimulus_name')

        self._metadata.to_nwb(nwbfile=nwbfile)
        self._probes.to_nwb(nwbfile=nwbfile)
        self._optotagging_table.to_nwb(nwbfile=nwbfile)
        return nwbfile

    @classmethod
    def from_nwb(
            cls,
            nwbfile: NWBFile,
            **kwargs
    ) -> "BehaviorEcephysSession":
        """

        Parameters
        ----------
        nwbfile
        kwargs: kwargs sent to `BehaviorSession.from_nwb`

        Returns
        -------
        instantiated `BehaviorEcephysSession`
        """
        kwargs['add_is_change_to_stimulus_presentations_table'] = False
        behavior_session = BehaviorSession.from_nwb(
            nwbfile=nwbfile,
            **kwargs
        )
        return BehaviorEcephysSession(
            behavior_session=behavior_session,
            probes=Probes.from_nwb(nwbfile=nwbfile),
            optotagging_table=OptotaggingTable.from_nwb(nwbfile=nwbfile),
            metadata=BehaviorEcephysMetadata.from_nwb(nwbfile=nwbfile)
        )

    def _get_identifier(self) -> str:
        return str(self._metadata.ecephys_session_id)
