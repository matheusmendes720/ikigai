-- migrations/003_epistemic_priority_view.sql
CREATE VIEW IF NOT EXISTS v_epistemic_priority AS
SELECT 
    st.id AS study_topic_fk,
    st.title,
    st.ikigai_vector,
    st.transferability,
    st.depth_level AS current_depth,
    st.target_depth,
    (st.target_depth - st.depth_level) AS depth_gap,
    
    -- Débito cognitivo normalizado (0-1)
    COALESCE(
        CASE st.cognitive_debt_level 
            WHEN 'critical' THEN 1.0
            WHEN 'high' THEN 0.8
            WHEN 'medium' THEN 0.5
            WHEN 'low' THEN 0.2
            ELSE 0.0
        END, 0.0
    ) AS debt_interest_rate,
    
    -- Fator de bloqueio (quantas tasks pendentes dependem deste tópico)
    COALESCE((
        SELECT COUNT(DISTINCT bt.task_uuid)
        FROM backlog_tasks bt, json_each(bt.knowledge_prerequisites) AS kp
        WHERE kp.value->>'study_topic_fk' = st.id
        AND bt.status = 'pending'
        AND kp.value->>'status' = 'deficit'
    ), 0) AS block_factor,
    
    -- Vetor de receita (mapeado de IKIGAi)
    CASE st.ikigai_vector
        WHEN 'revenue' THEN 1.0
        WHEN 'market' THEN 0.8
        WHEN 'skill' THEN 0.6
        WHEN 'passion' THEN 0.4
        ELSE 0.5
    END AS revenue_vector,
    
    -- Multiplicador de política (ajuste sistêmico)
    CASE COALESCE((SELECT policy FROM policy_decisions ORDER BY date DESC LIMIT 1), 'MAINTAIN')
        WHEN 'PUSH' THEN 1.2
        WHEN 'MAINTAIN' THEN 1.0
        WHEN 'REDUCE' THEN 0.7
        WHEN 'RECOVER' THEN 0.4
        ELSE 1.0
    END AS policy_multiplier,
    
    -- CÁLCULO FINAL DO SCORE
    (
        (0.25 * CASE st.ikigai_vector WHEN 'revenue' THEN 1.0 WHEN 'market' THEN 0.8 ELSE 0.6 END) +
        (0.25 * COALESCE((SELECT COUNT(DISTINCT bt.task_uuid) FROM backlog_tasks bt, json_each(bt.knowledge_prerequisites) AS kp WHERE kp.value->>'study_topic_fk' = st.id AND bt.status = 'pending' AND kp.value->>'status' = 'deficit'), 0) / 5.0) +
        (0.20 * st.transferability) +
        (0.15 * COALESCE(CASE st.cognitive_debt_level WHEN 'critical' THEN 1.0 WHEN 'high' THEN 0.8 WHEN 'medium' THEN 0.5 WHEN 'low' THEN 0.2 ELSE 0.0 END, 0.0)) +
        (0.15 * (st.target_depth - st.depth_level) / 5.0)
    ) * 
    CASE COALESCE((SELECT policy FROM policy_decisions ORDER BY date DESC LIMIT 1), 'MAINTAIN')
        WHEN 'PUSH' THEN 1.2 WHEN 'MAINTAIN' THEN 1.0 WHEN 'REDUCE' THEN 0.7 WHEN 'RECOVER' THEN 0.4 ELSE 1.0
    END AS epistemic_score,
    
    -- Ranking dinâmico
    RANK() OVER (ORDER BY 
        (
            (0.25 * CASE st.ikigai_vector WHEN 'revenue' THEN 1.0 WHEN 'market' THEN 0.8 ELSE 0.6 END) +
            (0.25 * COALESCE((SELECT COUNT(DISTINCT bt.task_uuid) FROM backlog_tasks bt, json_each(bt.knowledge_prerequisites) AS kp WHERE kp.value->>'study_topic_fk' = st.id AND bt.status = 'pending' AND kp.value->>'status' = 'deficit'), 0) / 5.0) +
            (0.20 * st.transferability) +
            (0.15 * COALESCE(CASE st.cognitive_debt_level WHEN 'critical' THEN 1.0 WHEN 'high' THEN 0.8 WHEN 'medium' THEN 0.5 WHEN 'low' THEN 0.2 ELSE 0.0 END, 0.0)) +
            (0.15 * (st.target_depth - st.depth_level) / 5.0)
        ) * 
        CASE COALESCE((SELECT policy FROM policy_decisions ORDER BY date DESC LIMIT 1), 'MAINTAIN')
            WHEN 'PUSH' THEN 1.2 WHEN 'MAINTAIN' THEN 1.0 WHEN 'REDUCE' THEN 0.7 WHEN 'RECOVER' THEN 0.4 ELSE 1.0
        END DESC
    ) AS priority_rank

FROM study_topics st
WHERE st.status = 'active';
