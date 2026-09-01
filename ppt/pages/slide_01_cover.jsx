<Slide style={{ width: '1280px', height: '720px', background: '#FFFFFF', position: 'relative' }}>
    {/* 顶部深蓝实色条 */}
    <Box style={{ position: 'absolute', top: 0, left: 0, width: 1280, height: 12, background: '#1E4FA8' }} />

    {/* 中央标题区 */}
    <Box style={{ alignItems: 'center', paddingTop: 108, width: '100%' }}>
        <Box style={{ background: '#E8EFF8', borderRadius: 20, padding: '8px 28px', marginBottom: 30 }}>
            <Text style={{ fontSize: 20, color: '#1E4FA8', fontWeight: 600, letterSpacing: 2 }}>
                挑战杯"揭榜挂帅" XA-202610 · 通信基建工程数智化设计与交付
            </Text>
        </Box>
        <Text style={{ fontSize: 62, fontWeight: 'bold', color: '#0E3F8C', textAlign: 'center', lineHeight: 1.3 }}>
            S4 设计成果向施工指令自动转化
        </Text>
        <Text style={{ fontSize: 30, color: '#4A5568', marginTop: 18, textAlign: 'center' }}>
            —— 设计清单一键生成完整 BOM 施工指令包 ——
        </Text>
    </Box>

    {/* 流水线定位图：S1 → S3 → S4 → S5（S4 高亮） */}
    <Box style={{ width: '100%', justifyContent: 'center', alignItems: 'center', marginTop: 62 }}>
        <svg width="1080" height="150" viewBox="0 0 1080 150">
            {/* S1 */}
            <rect x="20" y="35" width="200" height="80" rx="12" fill="#F0F5FC" stroke="#D6DCE5" stroke-width="1.5" />
            <text x="120" y="68" text-anchor="middle" font-size="20" font-weight="bold" fill="#4A5568">S1 智能设计</text>
            <text x="120" y="96" text-anchor="middle" font-size="15" fill="#8B97A8">设计清单输出方</text>
            {/* 箭头1 */}
            <line x1="228" y1="75" x2="292" y2="75" stroke="#8B97A8" stroke-width="2.5" />
            <polygon points="292,69 304,75 292,81" fill="#8B97A8" />
            {/* S3 */}
            <rect x="310" y="35" width="200" height="80" rx="12" fill="#F0F5FC" stroke="#D6DCE5" stroke-width="1.5" />
            <text x="410" y="68" text-anchor="middle" font-size="20" font-weight="bold" fill="#4A5568">S3 智能审查</text>
            <text x="410" y="96" text-anchor="middle" font-size="15" fill="#8B97A8">规则校验与分级</text>
            {/* 箭头2（进入S4，蓝色强调） */}
            <line x1="518" y1="75" x2="582" y2="75" stroke="#1E4FA8" stroke-width="3" />
            <polygon points="582,68 596,75 582,82" fill="#1E4FA8" />
            {/* S4 高亮块 */}
            <rect x="600" y="20" width="230" height="110" rx="14" fill="#1E4FA8" />
            <rect x="594" y="14" width="242" height="122" rx="16" fill="none" stroke="#1E4FA8" stroke-width="1.5" opacity="0.35" />
            <text x="715" y="60" text-anchor="middle" font-size="24" font-weight="bold" fill="#FFFFFF">S4 施工指令转化</text>
            <text x="715" y="92" text-anchor="middle" font-size="15" fill="#E8EFF8">BOM · 工序 · 纤芯</text>
            {/* 箭头3 */}
            <line x1="838" y1="75" x2="902" y2="75" stroke="#1E4FA8" stroke-width="3" />
            <polygon points="902,68 916,75 902,82" fill="#1E4FA8" />
            {/* S5 */}
            <rect x="922" y="35" width="200" height="80" rx="12" fill="#F0F5FC" stroke="#D6DCE5" stroke-width="1.5" />
            <text x="1022" y="68" text-anchor="middle" font-size="20" font-weight="bold" fill="#4A5568">S5 施工监管</text>
            <text x="1022" y="96" text-anchor="middle" font-size="15" fill="#8B97A8">现场执行验真</text>
        </svg>
    </Box>

    {/* 底部信息条 */}
    <Box style={{ position: 'absolute', bottom: 0, left: 0, width: 1280, height: 66, background: '#F7F9FC', flexDirection: 'row', justifyContent: 'center', alignItems: 'center', borderTop: '1px solid #E5E7EB' }}>
        <Text style={{ fontSize: 17, color: '#4A5568' }}>
            子赛题负责人：庞（nosh1816）　｜　全流水线第 4 环　｜　2026 年 8 月
        </Text>
    </Box>
</Slide>
