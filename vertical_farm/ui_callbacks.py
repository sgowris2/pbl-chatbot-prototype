import streamlit as st


def _update_monthly_changes(type: str, level=None, var=None, val=None, key=None, plant=None, num_plants=0):
    if key:
        val = st.session_state.get(key, val)
    if type == 'environment':
        if val == st.session_state.month_start_state['env'][var]:
            st.session_state.month_changes[st.session_state.month]['environment'][var] = None
        else:
            st.session_state.month_changes[st.session_state.month]['environment'][var] = val
        st.session_state._environment_controls_expanded = True
        st.session_state._inputs_expanded[level] = False
        st.session_state._plant_seeds_expanded[level] = False


    elif type == 'inputs':
        if val == st.session_state.month_start_state['levels'][level][var]:
            st.session_state.month_changes[st.session_state.month]['levels'][level][var] = None
        else:
            st.session_state.month_changes[st.session_state.month]['levels'][level][var] = val
        st.session_state._inputs_expanded[level] = True
        st.session_state._environment_controls_expanded = False
        st.session_state._plant_seeds_expanded[level] = False

    elif type == 'new_plants':
        st.session_state.month_changes[st.session_state.month]['levels'][level]['new_plants'][plant] = num_plants
        st.session_state._plant_seeds_expanded[level] = True

    elif type == 'removed_plants':
        if plant in st.session_state.month_changes[st.session_state.month]['levels'][level]['new_plants']:
            st.session_state.month_changes[st.session_state.month]['levels'][level]['new_plants'][plant] -= num_plants
            st.session_state.month_changes[st.session_state.month]['levels'][level]['new_plants'][plant] = (
                max(0, st.session_state.month_changes[st.session_state.month]['levels'][level]['new_plants'][plant]))
        st.session_state._plant_seeds_expanded[level] = True
        st.session_state._environment_controls_expanded = False
        st.session_state._inputs_expanded[level] = False

    else:
        # TODO : Add warning for unknown type
        return


def _disable_simulate():
    st.session_state["simulate_disabled"] = True


def _check_justifications(notes=None):
    if notes is None:
        notes = st.session_state.get("monthly_notes", "")
    st.session_state["simulate_disabled"] = notes.strip() == ""
