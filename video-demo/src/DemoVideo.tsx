import { AbsoluteFill, Easing, Img, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";

const FPS = 30;

// 设计令牌（与 PPT 配色一致）
const NAVY = "#1a365d";
const NAVY_DARK = "#102440";
const GREEN = "#38a169";
const ORANGE = "#dd6b20";
const LIGHT = "#f7fafc";
const SUB = "#cbd5e0";

// 字幕条：底部安全区内，大字号（4K 画幅）；跟随场景时长淡入淡出
const Subtitle = ({ text, durationInFrames }: { text: string; durationInFrames: number }) => {
  const frame = useCurrentFrame();
  const fadeOutStart = durationInFrames - Math.min(FPS, durationInFrames * 0.3);
  const opacity = interpolate(frame, [0, 8, fadeOutStart, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 140 }}>
      <div
        style={{
          opacity,
          background: "rgba(16,36,64,0.88)",
          borderRadius: 24,
          padding: "28px 64px",
          maxWidth: 3200,
        }}
      >
        <div style={{ color: "#fff", fontSize: 64, fontWeight: 700, textAlign: "center", lineHeight: 1.4 }}>{text}</div>
      </div>
    </AbsoluteFill>
  );
};

// 截图展示场景：淡入 + 轻推镜 + 底部字幕
const ScreenshotScene = ({ image, caption, durationInFrames }: { image: string; caption: string; durationInFrames: number }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const scale = interpolate(frame, [0, durationInFrames], [1.02, 1.1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: NAVY_DARK }}>
      <AbsoluteFill style={{ opacity, justifyContent: "center", alignItems: "center" }}>
        <div
          style={{
            width: 3200,
            height: 1800,
            borderRadius: 32,
            overflow: "hidden",
            boxShadow: "0 40px 120px rgba(0,0,0,0.55)",
            border: `6px solid ${NAVY}`,
            backgroundColor: "#fff",
          }}
        >
          <Img
            src={staticFile(image)}
            style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top", transform: `scale(${scale})` }}
          />
        </div>
      </AbsoluteFill>
      <Sequence from={10} durationInFrames={durationInFrames - 10}>
        <Subtitle text={caption} durationInFrames={durationInFrames - 10} />
      </Sequence>
    </AbsoluteFill>
  );
};

// 标题卡场景
const TitleScene = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 25], [80, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const subOpacity = interpolate(frame, [15, 35], [0, 1], { extrapolateRight: "clamp" });
  const agents = ["脑电卫士", "影像卫士", "健康卫士", "权益管家", "报销助手", "政策参谋", "安全守门"];
  return (
    <AbsoluteFill style={{ backgroundColor: NAVY, justifyContent: "center", alignItems: "center" }}>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 16, backgroundColor: GREEN }} />
      <div style={{ opacity: titleOpacity, translate: `0px ${titleY}px`, textAlign: "center" }}>
        <div style={{ color: "#fff", fontSize: 200, fontWeight: 800, letterSpacing: 4 }}>MedSignal</div>
      </div>
      <div style={{ opacity: subOpacity, textAlign: "center", marginTop: 48 }}>
        <div style={{ color: SUB, fontSize: 84, fontWeight: 700 }}>多模态医疗信号智能体</div>
        <div style={{ color: GREEN, fontSize: 56, fontWeight: 600, marginTop: 28 }}>关键医疗信号识别 × 患者信息连接</div>
      </div>
      <div
        style={{
          display: "flex",
          gap: 36,
          marginTop: 110,
        }}
      >
        {agents.map((a, i) => {
          const aOpacity = interpolate(frame, [40 + i * 5, 55 + i * 5], [0, 1], { extrapolateRight: "clamp" });
          return (
            <div
              key={a}
              style={{
                opacity: aOpacity,
                background: i < 3 ? GREEN : NAVY_DARK,
                border: `3px solid ${i < 3 ? GREEN : SUB}`,
                borderRadius: 999,
                padding: "22px 44px",
                color: "#fff",
                fontSize: 44,
                fontWeight: 700,
              }}
            >
              {a}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 60, color: SUB, fontSize: 44 }}>
        VentureD Hackathon · 医疗赛道
      </div>
    </AbsoluteFill>
  );
};

// 结尾金句场景
const ClosingScene = () => {
  const frame = useCurrentFrame();
  const l1 = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });
  const l2 = interpolate(frame, [15, 33], [0, 1], { extrapolateRight: "clamp" });
  const l3 = interpolate(frame, [30, 48], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: NAVY, justifyContent: "center", alignItems: "center" }}>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 16, backgroundColor: GREEN }} />
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 40 }}>
        <div style={{ color: SUB, fontSize: 72, opacity: l1, fontWeight: 600 }}>让关键医疗信号</div>
        <div style={{ color: ORANGE, fontSize: 140, opacity: l2, fontWeight: 800 }}>不再被错过</div>
        <div style={{ color: GREEN, fontSize: 56, opacity: l3, fontWeight: 700 }}>识别信号 · 守护健康 · 连接资源</div>
      </div>
      <div style={{ position: "absolute", bottom: 70, color: SUB, fontSize: 48 }}>MedSignal Team · 谢谢观看</div>
    </AbsoluteFill>
  );
};

// 主合成：90 秒 = 2700 帧 @30fps
// 分镜：0-8 痛点 | 8-15 标题 | 15-30 首页预警 | 30-50 脑电 | 50-65 政策 |
//       65-78 影像 | 78-86 数据空间(用聊天页) | 86-90 结尾
export const DemoVideo = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: NAVY_DARK }}>
      <Sequence durationInFrames={8 * FPS}>
        <PainScene />
      </Sequence>
      <Sequence from={8 * FPS} durationInFrames={7 * FPS}>
        <TitleScene />
      </Sequence>
      <Sequence from={15 * FPS} durationInFrames={15 * FPS}>
        <ScreenshotScene image="rehearsal_01_home.png" caption="登录即推送健康预警 · 从被动报销到主动健康" durationInFrames={15 * FPS} />
      </Sequence>
      <Sequence from={30 * FPS} durationInFrames={20 * FPS}>
        <ScreenshotScene image="rehearsal_04b_eeg_after_capture.png" caption="脑血管 · 认知 · 精神三大风险量化，每条预警可展开证据" durationInFrames={20 * FPS} />
      </Sequence>
      <Sequence from={50 * FPS} durationInFrames={15 * FPS}>
        <ScreenshotScene image="rehearsal_06_policy.png" caption="脑电异常自动推荐医保政策 · 一年可省数千元" durationInFrames={15 * FPS} />
      </Sequence>
      <Sequence from={65 * FPS} durationInFrames={13 * FPS}>
        <ScreenshotScene image="rehearsal_05c_imaging_viewer.png" caption="AI 检测框 vs 医师复核 —— 医师在环的安全闭环" durationInFrames={13 * FPS} />
      </Sequence>
      <Sequence from={78 * FPS} durationInFrames={8 * FPS}>
        <ScreenshotScene image="rehearsal_03_chat_reply.png" caption="多智能体协作 · 可信数据空间「可用不可见」" durationInFrames={8 * FPS} />
      </Sequence>
      <Sequence from={86 * FPS} durationInFrames={4 * FPS}>
        <ClosingScene />
      </Sequence>
    </AbsoluteFill>
  );
};

// 痛点开场：三行痛点文案逐行浮现
const PainScene = () => {
  const frame = useCurrentFrame();
  const lines = [
    { text: "交了这么多年医保", color: SUB },
    { text: "用的时候，却看不懂", color: "#fff" },
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: NAVY_DARK, justifyContent: "center", alignItems: "center" }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 56 }}>
        {lines.map((l, i) => {
          const o = interpolate(frame, [i * 20, i * 20 + 20], [0, 1], { extrapolateRight: "clamp" });
          const y = interpolate(frame, [i * 20, i * 20 + 25], [60, 0], {
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          });
          return (
            <div key={l.text} style={{ opacity: o, translate: `0px ${y}px`, color: l.color, fontSize: 110, fontWeight: 800 }}>
              {l.text}
            </div>
          );
        })}
        <div
          style={{
            opacity: interpolate(frame, [50, 70], [0, 1], { extrapolateRight: "clamp" }),
            color: ORANGE,
            fontSize: 72,
            fontWeight: 700,
          }}
        >
          关键医疗信号，正在被错过
        </div>
      </div>
    </AbsoluteFill>
  );
};
