from model.fitness_exercise import FitnessExercise
from model.fitness_plan import FitnessPlan
from model.fitness_plan_day import FitnessPlanDay
from model.fitness_plan_exercise import FitnessPlanExercise


DEFAULT_PLAN_NAME = '12周力量与俄挺计划'


EXERCISES = [
    ('俄挺前倾支撑', 'skill', '核心/肩胛', '俯卧撑支架', 'duration', '手臂打直，肩胛前伸，骨盆后倾。', '手腕或肩部疼痛时立即降低前倾角度。', '4组均达到20秒后增加前倾角度。'),
    ('杠铃卧推', 'strength', '胸', '杠铃', 'reps', '肩胛后缩下沉，双脚稳定，动作全程可控。', '肩前侧疼痛时先减重并检查肩胛位置。', '全组达到次数上限且RIR不少于1时小幅加重。'),
    ('上斜卧推', 'strength', '上胸', '杠铃', 'reps', '凳角保持约20–35度，杠铃落点稳定。', '凳角过高会更多刺激肩部。', '6–10次稳定后小幅加重。'),
    ('上斜哑铃卧推', 'strength', '上胸', '哑铃', 'reps', '控制下放，保持肩胛稳定。', '肩部不适时缩小下放幅度。', '达到次数上限后增加最小重量。'),
    ('支架俯卧撑', 'strength', '胸', '俯卧撑支架', 'reps', '保持身体成直线，利用支架获得更深拉伸。', '肩前侧不适时减少深度。', '先增加标准次数，再增加负重。'),
    ('哑铃飞鸟', 'strength', '胸', '哑铃', 'reps', '肘部微屈，以胸部拉伸为准控制下放。', '不要过度下放。', '10–15次稳定后小幅加重。'),
    ('哑铃侧平举', 'strength', '侧肩', '哑铃', 'reps', '肘部略弯，控制离心，顶端不耸肩。', '不要甩动重量。', '12–20次全程可控后加重。'),
    ('仰卧臂屈伸', 'strength', '三头', '哑铃', 'reps', '保持上臂稳定，控制肘部轨迹。', '肘部不适时减重或更换动作。', '达到次数上限后小幅加重。'),
    ('过顶哑铃臂屈伸', 'strength', '三头', '哑铃', 'reps', '保持上臂稳定，感受三头长头拉伸。', '肘部不适时减重或改用仰卧版本。', '10–15次稳定后加重。'),
    ('杠铃深蹲', 'strength', '腿/核心', '杠铃', 'reps', '深度保持一致，膝盖与脚尖方向一致。', '膝髋不适时先降低训练量。', '动作深度一致且达到次数上限后加重。'),
    ('罗马尼亚硬拉', 'strength', '后链', '杠铃/哑铃', 'reps', '髋部折叠，脊柱保持中立。', '腰背不稳时停止加重，不追求触地。', '髋折叠稳定后再加重。'),
    ('保加利亚分腿蹲', 'strength', '单腿', '哑铃/自重', 'reps', '躯干稳定，控制下放速度。', '膝髋不适时减少幅度或改用自重。', '先增加次数，稳定后再负重。'),
    ('壶铃摆动', 'strength', '臀/后链', '10kg壶铃', 'reps', '以髋部爆发发力，不要做成深蹲。', '腰背代偿时停止。', '先练稳定髋铰链，再增加次数。'),
    ('健腹轮', 'strength', '腹', '健腹轮', 'reps', '骨盆后倾，腰部不要塌陷。', '腰痛时改做死虫。', '动作稳定后逐步增加次数和活动范围。'),
    ('俄挺团身收膝', 'skill', '核心/肩胛', '俯卧撑支架', 'duration', '肩胛前伸，手臂打直，膝盖靠近胸部。', '不要为了抬脚而耸肩。', '稳定15秒后进入高级团身。'),
    ('蛙式支撑', 'skill', '核心/肩胛', '俯卧撑支架', 'duration', '保持肩胛主动前伸，逐步减少膝部支撑。', '手腕或肘部疼痛时退阶。', '稳定15秒后尝试团身俄挺。'),
    ('引体向上', 'strength', '背/二头', '单杠', 'reps', '全程下放，胸部尽量靠近杆。', '避免半程和耸肩刷次数。', '逐周增加总次数，达到上限后再负重。'),
    ('杠铃划船', 'strength', '厚背', '杠铃', 'reps', '拉向下腹，保持躯干角度不变。', '下背疲劳时减量。', '躯干稳定且达到次数上限后加重。'),
    ('单臂哑铃划船', 'strength', '背阔', '哑铃', 'reps', '肘部拉向髋部，避免耸肩。', '躯干旋转明显时减重。', '双侧都达到次数上限后加重。'),
    ('俯身后束飞鸟', 'strength', '后束', '哑铃', 'reps', '使用轻重量并保持高控制。', '不要借力甩动。', '高次数稳定后小幅加重。'),
    ('杠铃弯举', 'strength', '二头', '杠铃', 'reps', '上臂固定，避免身体摆动。', '手腕或肘部不适时减重。', '达到次数上限且动作标准后加重。'),
    ('哑铃弯举', 'strength', '二头', '哑铃', 'reps', '上臂固定，完整控制离心。', '不要借力甩动。', '达到次数上限后增加最小重量。'),
    ('伪俄挺俯卧撑', 'skill', '胸/肩胛/核心', '俯卧撑支架', 'reps', '肩部保持在手前，身体成一条直线。', '塌腰或肩痛时降低难度。', '3组8次稳定后增加前倾角度。'),
    ('低杠实力推过渡练习', 'skill', '背/肩/手臂', '深蹲架横杠/单杠', 'reps', '先练翻腕过渡和顶杆支撑，可用脚部辅助。', '不练到力竭，肩肘疼痛时停止。', '过渡不塌肩且顶杆稳定后减少脚部辅助。'),
    ('反向划船', 'strength', '背/水平拉', '深蹲架横杠/自重', 'reps', '胸部贴近杠，肩胛后缩下沉，身体成直线。', '腰部下沉时降低难度。', '达到次数上限后降低横杠高度。'),
    ('上斜哑铃弯举', 'strength', '二头', '哑铃', 'reps', '上臂固定，保持二头长头拉伸。', '肩或肘不适时调整凳角并减重。', '10–15次稳定后加重。'),
    ('臂力棒夹胸', 'strength', '胸/手臂', '40kg臂力棒', 'reps', '动作可控，作为训练末尾辅助。', '不要用它替代卧推主项。', '优先增加标准次数。'),
    ('前蹲', 'strength', '腿/核心', '杠铃', 'reps', '保持躯干直立，技术稳定优先。', '手腕或上背无法稳定时降低重量。', '技术稳定后小幅加重。'),
    ('暂停深蹲', 'strength', '腿/核心', '杠铃', 'reps', '底部保持张力后再起身。', '技术日不要练到动作崩坏。', '深度和停顿一致后小幅加重。'),
    ('相扑硬拉', 'strength', '后链/臀', '杠铃', 'reps', '选择髋部舒适站距，腿部主动发力。', '背部无法保持中立时停止加重。', '达到次数上限且动作稳定后加重。'),
    ('悬垂举腿', 'strength', '腹', '单杠', 'reps', '控制骨盆，不依靠摆动。', '肩部不适时改用仰卧版本。', '先增加标准次数，再提高抬腿高度。'),
    ('仰卧举腿', 'strength', '腹', '自重', 'reps', '腰背贴稳地面，控制下放。', '腰部不适时缩小幅度。', '达到次数上限后增加离心时间。'),
    ('杠铃反握弯举', 'strength', '前臂/握力', '杠铃', 'reps', '手腕保持中立，避免甩动。', '手腕不适时立即减重或停止。', '10–15次稳定后小幅加重。'),
    ('轻松走路', 'cardio', '恢复', '自重', 'duration', '保持能够正常说话的轻松强度。', None, '以恢复为目的，不追求疲劳。'),
    ('肩胸髋灵活性', 'mobility', '恢复', '自重/支架', 'duration', '在无痛范围活动肩、胸和髋。', '出现锐痛时停止。', '保持规律，不追求极限幅度。'),
    ('周训练复盘', 'recovery', '恢复', '手机/笔记', 'check', '检查体重、腰围、训练完成率与疲劳。', None, '据此决定下周加重、维持或减量。'),
]


WEEK = [
    (1, '上肢A', '胸 / 推 / 三头 + 俄挺技能', False, 85, [
        ('俄挺前倾支撑', 4, None, (10, 20), None, 60, '先加时间', '身体前倾到可控，肩胛前伸。'),
        ('杠铃卧推', 4, (5, 8), None, (1, 2), 180, '双进阶', '选择能完成5次且剩1–2次余力的重量。'),
        ('上斜卧推', 3, (6, 10), None, (1, 2), 120, '双进阶', '凳角约20–35度。'),
        ('支架俯卧撑', 3, (10, 15), None, (1, 2), 90, '先加次数', '自重起步，保持完整活动范围。'),
        ('哑铃侧平举', 4, (12, 20), None, (1, 2), 75, '先加次数', '轻重量高控制。'),
        ('过顶哑铃臂屈伸', 3, (10, 15), None, (1, 2), 90, '先加次数', '肘部舒适优先。'),
    ]),
    (2, '下肢A', '深蹲 / 后链 / 腹', False, 80, [
        ('杠铃深蹲', 4, (5, 8), None, (1, 2), 180, '双进阶', '动作深度保持一致。'),
        ('罗马尼亚硬拉', 3, (6, 10), None, (1, 2), 120, '双进阶', '背部保持中立。'),
        ('保加利亚分腿蹲', 3, (8, 12), None, (1, 2), 90, '先加次数', '每侧完成目标次数。'),
        ('壶铃摆动', 3, (15, 20), None, (2, 3), 60, '先练髋铰链', '使用10kg固定重量。'),
        ('健腹轮', 3, (6, 15), None, (1, 2), 75, '先加次数', '以腰不塌为准。'),
    ]),
    (3, '拉力A', '引体 / 划船 / 二头 + 俄挺技能', False, 85, [
        ('俄挺团身收膝', 4, None, (8, 15), None, 60, '先加时间', '选择能稳定停住的版本。'),
        ('引体向上', 5, (3, 8), None, (1, 2), 180, '先加总次数', '自重能完成3次起步。'),
        ('杠铃划船', 4, (6, 10), None, (1, 2), 120, '双进阶', '躯干角度保持不变。'),
        ('单臂哑铃划船', 3, (8, 12), None, (1, 2), 90, '双进阶', '每侧分别完成。'),
        ('俯身后束飞鸟', 3, (12, 20), None, (1, 2), 75, '先加次数', '轻重量高控制。'),
        ('杠铃弯举', 3, (8, 12), None, (1, 2), 90, '双进阶', '动作标准，不借力。'),
    ]),
    (4, '主动恢复', '走路 / 拉伸', True, 30, [
        ('轻松走路', None, None, (1200, 2400), None, None, None, '保持能正常说话的强度。'),
        ('肩胸髋灵活性', 2, None, (300, 600), None, None, None, '只在无痛范围活动。'),
    ]),
    (5, '上肢B', '上胸 / 背 / 手臂 + 俄挺、实力推技能', False, 85, [
        ('伪俄挺俯卧撑', 3, (5, 8), None, (1, 2), 90, '先加次数', '在支架上保持可控前倾。'),
        ('上斜卧推', 4, (6, 10), None, (1, 2), 120, '双进阶', '上胸主项。'),
        ('低杠实力推过渡练习', 4, (3, 5), None, None, 90, '先练动作', '主项前做，不追求一次标准实力推。'),
        ('反向划船', 3, (8, 12), None, (1, 2), 90, '先加次数', '调整横杠到合适高度。'),
        ('哑铃侧平举', 4, (12, 20), None, (1, 2), 60, '先加次数', '控制离心。'),
        ('上斜哑铃弯举', 3, (10, 15), None, (1, 2), 75, '先加次数', '超级组A。'),
        ('过顶哑铃臂屈伸', 3, (10, 15), None, (1, 2), 75, '先加次数', '超级组A。'),
        ('臂力棒夹胸', 2, (8, 12), None, (2, 2), 60, '先加次数', '40kg，仅作为辅助。'),
    ]),
    (6, '下肢B', '腿 / 核心 / 握力', False, 70, [
        ('暂停深蹲', 3, (5, 8), None, (1, 2), 180, '小幅加重', '技术稳定优先。'),
        ('相扑硬拉', 3, (5, 8), None, (1, 2), 180, '双进阶', '背部保持中立。'),
        ('保加利亚分腿蹲', 2, (8, 12), None, (1, 2), 90, '先加次数', '每侧分别完成。'),
        ('悬垂举腿', 3, (8, 15), None, (1, 2), 75, '先加次数', '以不摆动为准。'),
        ('杠铃反握弯举', 3, (10, 15), None, (1, 2), 75, '先加次数', '轻中重量，不甩动。'),
    ]),
    (7, '恢复与复盘', '睡眠 / 饮食 / 数据复盘', True, 15, [
        ('周训练复盘', None, None, None, None, None, None, '决定下周是否加重、维持或减量。'),
    ]),
]


def ensure_default_fitness_data(db, user_identity):
    exercises = FitnessExercise.query.filter_by(user_identity=user_identity).all()
    by_name = {exercise.name: exercise for exercise in exercises}

    for row in EXERCISES:
        name, category, muscle, equipment, metric, instructions, cautions, progression = row
        if name in by_name:
            continue
        exercise = FitnessExercise(
            user_identity=user_identity,
            name=name,
            category=category,
            primary_muscle=muscle,
            equipment=equipment,
            metric_type=metric,
            instructions=instructions,
            cautions=cautions,
            progression_notes=progression,
        )
        db.session.add(exercise)
        by_name[name] = exercise

    db.session.flush()

    existing_plan = FitnessPlan.query.filter_by(
        user_identity=user_identity,
        name=DEFAULT_PLAN_NAME,
    ).first()
    if existing_plan:
        db.session.commit()
        return existing_plan

    plan = FitnessPlan(
        user_identity=user_identity,
        name=DEFAULT_PLAN_NAME,
        description='每周5练；多数工作组保留1–2 RIR；第4、8、12周根据疲劳安排减量。',
        duration_weeks=12,
        is_active=True,
    )
    db.session.add(plan)

    for weekday, name, focus, is_rest, minutes, items in WEEK:
        day = FitnessPlanDay(
            plan=plan,
            weekday=weekday,
            name=name,
            focus=focus,
            is_rest=is_rest,
            estimated_minutes=minutes,
        )
        db.session.add(day)
        for index, item in enumerate(items, start=1):
            exercise_name, sets, reps, duration, rir, rest, progression, notes = item
            exercise = by_name[exercise_name]
            plan_exercise = FitnessPlanExercise(
                plan_day=day,
                exercise=exercise,
                sort_order=index,
                sets=sets,
                reps_min=reps[0] if reps else None,
                reps_max=reps[1] if reps else None,
                duration_seconds_min=duration[0] if duration else None,
                duration_seconds_max=duration[1] if duration else None,
                rir_min=rir[0] if rir else None,
                rir_max=rir[1] if rir else None,
                rest_seconds=rest,
                progression_type=progression,
                plan_notes=notes,
                each_side=exercise_name in ('保加利亚分腿蹲', '单臂哑铃划船'),
                superset_group='A'
                if weekday == 5 and exercise_name in ('上斜哑铃弯举', '过顶哑铃臂屈伸')
                else None,
            )
            db.session.add(plan_exercise)

    db.session.commit()
    return plan
