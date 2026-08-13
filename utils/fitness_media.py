import os


FITNESS_CDN_BASE_URL = os.getenv(
    'FITNESS_CDN_BASE_URL',
    'https://img.tt829.cn',
).rstrip('/')


# name: (slug, match type, extension, note)
EXERCISE_MEDIA = {
    '俄挺前倾支撑': ('planche-lean', 'related', 'png', '俯卧支撑姿势参考；前倾支撑应按动作要点完成。'),
    '杠铃卧推': ('barbell-bench-press', 'exact', 'png', None),
    '上斜卧推': ('incline-barbell-bench-press', 'exact', 'png', None),
    '上斜哑铃卧推': ('incline-dumbbell-bench-press', 'exact', 'png', None),
    '支架俯卧撑': ('support-push-up', 'related', 'png', '标准俯卧撑轨迹参考；支架版本保持腕部中立。'),
    '哑铃飞鸟': ('dumbbell-fly', 'exact', 'png', None),
    '哑铃侧平举': ('dumbbell-lateral-raise', 'exact', 'png', None),
    '仰卧臂屈伸': ('lying-triceps-extension', 'exact', 'png', None),
    '过顶哑铃臂屈伸': ('overhead-dumbbell-triceps-extension', 'exact', 'png', None),
    '杠铃深蹲': ('barbell-back-squat', 'related', 'png', '深蹲起止姿势参考；实际训练节奏以计划要求为准。'),
    '罗马尼亚硬拉': ('romanian-deadlift', 'exact', 'png', None),
    '保加利亚分腿蹲': ('bulgarian-split-squat', 'related', 'png', '单腿蹲动作模式参考；后脚应置于支撑面。'),
    '壶铃摆动': ('kettlebell-swing', 'exact', 'svg', None),
    '健腹轮': ('ab-rollout', 'related', 'png', '跪姿滚动轨迹参考；示意器械为杠铃。'),
    '俄挺团身收膝': ('tuck-planche-knee-tuck', 'related', 'png', '俯卧支撑姿势参考；团身收膝为进阶过渡动作。'),
    '蛙式支撑': ('frog-stand', 'related', 'png', '手臂支撑姿势参考；蛙式支撑按动作要点降低难度。'),
    '引体向上': ('pull-up', 'exact', 'png', None),
    '杠铃划船': ('barbell-row', 'related', 'png', '俯身杠铃划船轨迹参考；握法以计划配置为准。'),
    '单臂哑铃划船': ('one-arm-dumbbell-row', 'related', 'png', '哑铃划船模式参考；实际动作采用单臂支撑版本。'),
    '俯身后束飞鸟': ('bent-over-rear-delt-fly', 'related', 'png', '后束飞鸟轨迹参考；支撑方式可按器械调整。'),
    '杠铃弯举': ('barbell-curl', 'exact', 'png', None),
    '哑铃弯举': ('dumbbell-curl', 'exact', 'png', None),
    '伪俄挺俯卧撑': ('pseudo-planche-push-up', 'related', 'png', '俯卧撑轨迹参考；双手更靠近髋部并保持前倾。'),
    '低杠实力推过渡练习': ('low-bar-press-transition', 'related', 'png', '杠铃推举轨迹参考；握位和幅度以计划要点为准。'),
    '反向划船': ('inverted-row', 'exact', 'png', None),
    '上斜哑铃弯举': ('incline-dumbbell-curl', 'exact', 'png', None),
    '臂力棒夹胸': ('power-twister-chest', 'related', 'png', '胸部夹合发力方向参考；注意臂力棒回弹风险。'),
    '前蹲': ('front-squat', 'exact', 'png', None),
    '暂停深蹲': ('pause-squat', 'related', 'png', '深蹲姿势参考；在计划指定的最低点保持暂停。'),
    '相扑硬拉': ('sumo-deadlift', 'related', 'png', '宽站距姿势参考；动作仍需遵循硬拉要点。'),
    '悬垂举腿': ('hanging-leg-raise', 'related', 'png', '悬垂起始姿势参考；举腿时避免摆动。'),
    '仰卧举腿': ('lying-leg-raise', 'exact', 'png', None),
    '杠铃反握弯举': ('reverse-barbell-curl', 'related', 'png', '反握弯举轨迹参考；示意器械与计划器械不同。'),
    '轻松走路': ('easy-walking', 'related', 'png', '仅参考行进方向；轻松走路不需要做弓步。'),
    '肩胸髋灵活性': ('shoulder-chest-hip-mobility', 'related', 'png', '肩部活动轨迹参考；各部位按计划分别完成。'),
    '周训练复盘': ('weekly-training-review', 'informational', 'svg', '这是复盘任务，不是训练动作。'),
}


def media_for_exercise(name):
    config = EXERCISE_MEDIA.get(name)
    if not config:
        return None

    slug, match_type, extension, note = config
    base_url = f'{FITNESS_CDN_BASE_URL}/fitness/exercises/{slug}'
    if match_type == 'informational':
        images = [{'position': 'overview', 'url': f'{base_url}/overview.{extension}'}]
    else:
        images = [
            {'position': 'start', 'url': f'{base_url}/start.{extension}'},
            {'position': 'finish', 'url': f'{base_url}/finish.{extension}'},
        ]

    return {
        'matchType': match_type,
        'note': note,
        'images': images,
        'manifestUrl': f'{FITNESS_CDN_BASE_URL}/fitness/exercises/manifest.json',
    }
