/**
 * NotificationBell.jsx — Notifications + POD Preview & Download
 * ==============================================================
 * Bell with unread badge, dropdown, 60s auto-poll.
 * POD notifications have "View POD" button → shows images inline with download.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchNotifications, markNotificationRead, markAllNotificationsRead, viewPod } from '../api';

const C = {
  card:'#ffffff', bg:'#f8fafc', border:'#e2e8f0', text:'#0f172a',
  sub:'#475569', muted:'#94a3b8', teal:'#0d9488', tealDk:'#0f766e',
  blue:'#3b82f6', red:'#ef4444', green:'#10b981',
  shadow:'0 10px 30px rgba(0,0,0,0.10)',
};

const TYPE_ICONS = {
  shipment_assigned:'🚚', pod_uploaded:'📸',
  daily_pod_reminder:'⏰', general:'🔔',
};

function timeAgo(dateStr) {
  const diff = Date.now()-new Date(dateStr);
  const mins = Math.floor(diff/60000);
  if(mins<1) return 'just now';
  if(mins<60) return `${mins}m ago`;
  const hrs = Math.floor(mins/60);
  if(hrs<24) return `${hrs}h ago`;
  return `${Math.floor(hrs/24)}d ago`;
}

/** Download a single image by fetching as blob */
async function downloadImage(url, filename) {
  try {
    const res = await fetch(url);
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
  } catch {
    // fallback: open in new tab
    window.open(url, '_blank');
  }
}

export default function NotificationBell() {
  const [open, setOpen]       = useState(false);
  const [notifs, setNotifs]   = useState([]);
  const [unread, setUnread]   = useState(0);
  const [loading, setLoading] = useState(false);
  // POD preview
  const [podData, setPodData]     = useState(null);
  const [podLoading, setPodLoading] = useState(null); // shipment_ref loading
  const [downloading, setDownloading] = useState(null); // idx or 'all'
  const dropdownRef = useRef(null);

  const load = useCallback(async()=>{
    setLoading(true);
    try{
      const data=await fetchNotifications({page_size:15});
      setNotifs(data.results||[]); setUnread(data.unread_count||0);
    }catch{}
    setLoading(false);
  },[]);

  useEffect(()=>{load();},[load]);
  useEffect(()=>{
    const id=setInterval(load,60_000);
    return()=>clearInterval(id);
  },[load]);

  useEffect(()=>{
    const h=e=>{if(dropdownRef.current&&!dropdownRef.current.contains(e.target))setOpen(false);};
    document.addEventListener('mousedown',h);
    return()=>document.removeEventListener('mousedown',h);
  },[]);

  async function handleRead(id) {
    await markNotificationRead(id);
    setNotifs(p=>p.map(n=>n.id===id?{...n,is_read:true}:n));
    setUnread(p=>Math.max(0,p-1));
  }
  async function handleMarkAll() {
    await markAllNotificationsRead();
    setNotifs(p=>p.map(n=>({...n,is_read:true})));
    setUnread(0);
  }

  async function handleViewPod(shipmentRef, e) {
    e.stopPropagation();
    if(!shipmentRef) return;
    setPodLoading(shipmentRef);
    try {
      const data = await viewPod(shipmentRef);
      setPodData(data);
    } catch(err) { alert('Failed to load POD: '+err.message); }
    setPodLoading(null);
  }

  async function handleDownloadOne(img, idx) {
    setDownloading(idx);
    const filename = `POD_${podData.shipment_id}_Photo${img.index}.jpg`;
    await downloadImage(img.url, filename);
    setDownloading(null);
  }

  async function handleDownloadAll() {
    if(!podData?.images?.length) return;
    setDownloading('all');
    for(let i=0;i<podData.images.length;i++){
      const img = podData.images[i];
      const filename = `POD_${podData.shipment_id}_Photo${img.index}.jpg`;
      await downloadImage(img.url, filename);
      // small gap so browser doesn't block multiple downloads
      await new Promise(r=>setTimeout(r,500));
    }
    setDownloading(null);
  }

  return (
    <>
      <div ref={dropdownRef} style={{ position:'relative' }}>
        {/* Bell */}
        <button id="notif-bell-btn"
          onClick={()=>{setOpen(o=>!o);if(!open)load();}}
          style={{
            position:'relative', background:open?`${C.teal}10`:'transparent',
            border:`1px solid ${open?C.teal+'50':C.border}`,
            borderRadius:'8px', padding:'0.45rem 0.6rem',
            cursor:'pointer', fontSize:'1.1rem', lineHeight:1,
          }}>
          🔔
          {unread>0&&(
            <span style={{
              position:'absolute',top:'-5px',right:'-5px',
              background:C.red,color:'#fff',borderRadius:'999px',
              fontSize:'0.62rem',fontWeight:700,
              minWidth:'17px',height:'17px',
              display:'flex',alignItems:'center',justifyContent:'center',
              padding:'0 2px',border:'2px solid #fff',
            }}>{unread>99?'99+':unread}</span>
          )}
        </button>

        {/* Dropdown */}
        {open&&(
          <div style={{
            position:'absolute',top:'calc(100% + 8px)',right:0,
            width:'380px',maxHeight:'500px',
            background:C.card,border:`1px solid ${C.border}`,
            borderRadius:'12px',boxShadow:C.shadow,zIndex:1000,
            display:'flex',flexDirection:'column',overflow:'hidden',
          }}>
            {/* Header */}
            <div style={{
              padding:'0.85rem 1rem',borderBottom:`1px solid ${C.border}`,
              display:'flex',justifyContent:'space-between',alignItems:'center',
            }}>
              <span style={{ fontWeight:700,color:C.text,fontSize:'0.88rem' }}>
                🔔 Notifications {unread>0&&<span style={{color:C.teal}}>({unread})</span>}
              </span>
              {unread>0&&(
                <button onClick={handleMarkAll}
                  style={{ background:'none',border:'none',color:C.teal,fontSize:'0.75rem',cursor:'pointer',fontWeight:600 }}>
                  Mark all read
                </button>
              )}
            </div>

            {/* List */}
            <div style={{ overflowY:'auto',flex:1 }}>
              {loading&&notifs.length===0&&(
                <div style={{ padding:'2rem',textAlign:'center',color:C.muted,fontSize:'0.85rem' }}>Loading…</div>
              )}
              {!loading&&notifs.length===0&&(
                <div style={{ padding:'2rem',textAlign:'center',color:C.muted,fontSize:'0.85rem' }}>🎉 You're all caught up!</div>
              )}
              {notifs.map(n=>(
                <div key={n.id}
                  onClick={()=>!n.is_read&&handleRead(n.id)}
                  style={{
                    padding:'0.75rem 1rem',borderBottom:`1px solid ${C.border}`,
                    background:n.is_read?C.card:`${C.teal}06`,
                    cursor:n.is_read?'default':'pointer',
                  }}>
                  <div style={{ display:'flex',gap:'0.75rem',alignItems:'flex-start' }}>
                    <span style={{ fontSize:'1.2rem',flexShrink:0,marginTop:'1px' }}>
                      {TYPE_ICONS[n.notif_type]||'🔔'}
                    </span>
                    <div style={{ flex:1,minWidth:0 }}>
                      <div style={{ fontWeight:n.is_read?500:700,color:n.is_read?C.muted:C.text,fontSize:'0.83rem',marginBottom:'0.15rem' }}>
                        {n.title}
                      </div>
                      <div style={{ color:C.sub,fontSize:'0.76rem',lineHeight:1.4 }}>{n.message}</div>
                      {n.shipment_ref&&(
                        <div style={{ color:C.teal,fontSize:'0.7rem',marginTop:'0.2rem',fontWeight:600 }}>
                          CN: {n.shipment_ref}
                        </div>
                      )}
                      <div style={{ color:C.muted,fontSize:'0.67rem',marginTop:'0.25rem' }}>
                        {timeAgo(n.created_at)}
                      </div>
                    </div>
                    {!n.is_read&&(
                      <div style={{ width:'8px',height:'8px',borderRadius:'50%',background:C.teal,flexShrink:0,marginTop:'5px' }}/>
                    )}
                  </div>

                  {/* View POD button for pod_uploaded notifications */}
                  {n.notif_type==='pod_uploaded'&&n.shipment_ref&&(
                    <button
                      onClick={(e)=>handleViewPod(n.shipment_ref,e)}
                      disabled={podLoading===n.shipment_ref}
                      style={{
                        marginTop:'0.5rem', marginLeft:'2rem',
                        padding:'0.35rem 0.85rem',
                        background:podLoading===n.shipment_ref?C.muted:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
                        color:'#fff', border:'none', borderRadius:'6px',
                        fontSize:'0.75rem', fontWeight:700,
                        cursor:podLoading===n.shipment_ref?'not-allowed':'pointer',
                        fontFamily:'inherit',
                        display:'inline-flex',alignItems:'center',gap:'0.35rem',
                      }}>
                      {podLoading===n.shipment_ref ? '⏳ Loading...' : '📸 View POD'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* POD Preview Modal */}
      {podData&&(
        <div style={{
          position:'fixed',inset:0,background:'rgba(0,0,0,0.65)',
          backdropFilter:'blur(6px)',display:'flex',alignItems:'center',
          justifyContent:'center',zIndex:2000,padding:'1rem',
        }} onClick={e=>{if(e.target===e.currentTarget)setPodData(null);}}>
          <div style={{
            background:C.card,borderRadius:'18px',width:'100%',maxWidth:'560px',
            maxHeight:'90vh',overflow:'auto',boxShadow:'0 20px 50px rgba(0,0,0,0.25)',
          }}>

            {/* Modal Header */}
            <div style={{
              background:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
              padding:'1.1rem 1.25rem',color:'#fff',
              display:'flex',justifyContent:'space-between',alignItems:'center',
              borderRadius:'18px 18px 0 0',
              position:'sticky',top:0,zIndex:1,
            }}>
              <div>
                <div style={{ fontWeight:900,fontSize:'1.1rem' }}>📸 Proof of Delivery</div>
                <div style={{ fontSize:'0.78rem',opacity:0.85,marginTop:'0.15rem' }}>
                  {podData.shipment_id} · {podData.origin} → {podData.destination}
                </div>
              </div>
              <div style={{ display:'flex',gap:'0.5rem',alignItems:'center' }}>
                {/* Download All button */}
                {podData.images?.length>0&&(
                  <button
                    onClick={handleDownloadAll}
                    disabled={downloading==='all'}
                    title="Download all POD images"
                    style={{
                      padding:'0.4rem 0.85rem',
                      background: downloading==='all' ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.2)',
                      border:'1px solid rgba(255,255,255,0.5)',
                      color:'#fff',borderRadius:'8px',
                      fontSize:'0.75rem',fontWeight:700,cursor:downloading==='all'?'not-allowed':'pointer',
                      display:'flex',alignItems:'center',gap:'0.35rem',
                      backdropFilter:'blur(4px)',
                    }}>
                    {downloading==='all' ? '⏳ Downloading...' : '⬇ Download All'}
                  </button>
                )}
                <button onClick={()=>setPodData(null)} style={{
                  background:'rgba(255,255,255,0.2)',border:'none',color:'#fff',
                  borderRadius:'50%',width:'32px',height:'32px',cursor:'pointer',
                  fontSize:'1rem',display:'flex',alignItems:'center',justifyContent:'center',
                }}>✕</button>
              </div>
            </div>

            {/* Modal Body */}
            <div style={{ padding:'1.25rem' }}>
              {podData.images.length===0?(
                <div style={{ textAlign:'center',padding:'2rem',color:C.muted }}>
                  🚫 No photos found for this shipment
                </div>
              ):(
                <div style={{ display:'flex',flexDirection:'column',gap:'1rem' }}>
                  {/* Shipment Info */}
                  <div style={{
                    display:'grid',gridTemplateColumns:'1fr 1fr',gap:'0.5rem',
                    padding:'0.75rem',background:'#f8fafc',borderRadius:'10px',
                    border:`1px solid ${C.border}`,
                  }}>
                    <div>
                      <div style={{ fontSize:'0.6rem',color:C.muted,fontWeight:700,textTransform:'uppercase' }}>Vehicle No.</div>
                      <div style={{ fontSize:'0.85rem',fontWeight:600,color:C.text }}>{podData.vehicle_no||'—'}</div>
                    </div>
                    <div>
                      <div style={{ fontSize:'0.6rem',color:C.muted,fontWeight:700,textTransform:'uppercase' }}>Dispatch Date</div>
                      <div style={{ fontSize:'0.85rem',fontWeight:600,color:C.text }}>{podData.dispatch_date||'—'}</div>
                    </div>
                  </div>

                  {/* Each Photo */}
                  {podData.images.map((img,idx)=>(
                    <div key={idx} style={{
                      borderRadius:'12px',overflow:'hidden',
                      border:`2px solid ${C.teal}30`,
                      boxShadow:'0 2px 8px rgba(0,0,0,0.08)',
                    }}>
                      {/* Photo label + individual download */}
                      <div style={{
                        display:'flex',justifyContent:'space-between',alignItems:'center',
                        padding:'0.45rem 0.75rem',
                        background:`${C.teal}10`,
                        borderBottom:`1px solid ${C.teal}20`,
                      }}>
                        <span style={{ fontSize:'0.72rem',fontWeight:700,color:C.sub,textTransform:'uppercase' }}>
                          📷 Photo {img.index}
                        </span>
                        <button
                          onClick={()=>handleDownloadOne(img,idx)}
                          disabled={downloading===idx}
                          style={{
                            padding:'0.28rem 0.65rem',
                            background:downloading===idx?C.muted:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
                            color:'#fff',border:'none',borderRadius:'6px',
                            fontSize:'0.7rem',fontWeight:700,
                            cursor:downloading===idx?'not-allowed':'pointer',
                            display:'inline-flex',alignItems:'center',gap:'0.25rem',
                            fontFamily:'inherit',
                          }}>
                          {downloading===idx ? '⏳ Saving...' : '⬇ Download'}
                        </button>
                      </div>
                      <img src={img.url} alt={`POD ${img.index}`}
                        style={{ width:'100%',maxHeight:'320px',objectFit:'contain',display:'block',background:'#f1f5f9' }}/>
                    </div>
                  ))}

                  {podData.pod_uploaded_at&&(
                    <div style={{
                      textAlign:'center',fontSize:'0.75rem',color:C.muted,
                      padding:'0.5rem',background:'#f8fafc',borderRadius:'8px',
                    }}>
                      📅 Uploaded: {new Date(podData.pod_uploaded_at).toLocaleString('en-IN')}
                    </div>
                  )}
                </div>
              )}

              {/* Download All (bottom) + Close */}
              <div style={{ display:'flex',gap:'0.75rem',marginTop:'1rem' }}>
                {podData.images?.length>0&&(
                  <button
                    onClick={handleDownloadAll}
                    disabled={downloading==='all'}
                    style={{
                      flex:1,padding:'0.75rem',
                      background:downloading==='all'?C.muted:`linear-gradient(135deg, #3b82f6, #1d4ed8)`,
                      color:'#fff',border:'none',borderRadius:'10px',
                      fontWeight:700,fontSize:'0.88rem',cursor:downloading==='all'?'not-allowed':'pointer',
                      fontFamily:'inherit',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.4rem',
                    }}>
                    {downloading==='all' ? '⏳ Downloading All...' : '⬇ Download All Photos'}
                  </button>
                )}
                <button onClick={()=>setPodData(null)} style={{
                  flex:1,padding:'0.75rem',
                  background:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
                  color:'#fff',border:'none',borderRadius:'10px',
                  fontWeight:700,fontSize:'0.88rem',cursor:'pointer',fontFamily:'inherit',
                }}>✕ Close</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
