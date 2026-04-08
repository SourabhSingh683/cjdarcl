/**
 * DriverPanel.jsx — Hinglish Driver Panel
 * =========================================
 * Features:
 *   • Mera Load — assigned shipments
 *   • Photo Bhejo — 1-3 POD upload
 *   • Purana Record — completed + POD preview + Invoice view
 *   • NotificationBell — alerts from manager
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchDriverShipments, uploadPodImages, viewPod, getInvoiceUrl, deletePod } from '../api';
import NotificationBell from './NotificationBell';

// ── Status map ────────────────────────────────────────────────────────────────
const STATUS_MAP = {
  '':            { label: 'Load Mila',        color: '#3b82f6', bg: '#eff6ff',  icon: '📦' },
  'assigned':    { label: 'Load Mila',        color: '#3b82f6', bg: '#eff6ff',  icon: '📦' },
  'in_transit':  { label: 'Raaste Mein',      color: '#f59e0b', bg: '#fffbeb',  icon: '🚚' },
  'reached':     { label: 'Pahunch Gaya',     color: '#8b5cf6', bg: '#f5f3ff',  icon: '📍' },
  'Uploaded':    { label: 'Photo Bhej Diya',  color: '#10b981', bg: '#ecfdf5',  icon: '✅' },
  'pod_uploaded':{ label: 'Photo Bhej Diya',  color: '#10b981', bg: '#ecfdf5',  icon: '✅' },
};
function getStatus(s) {
  if (s.pod_status === 'Uploaded') return STATUS_MAP['Uploaded'];
  return STATUS_MAP[s.pod_status] || STATUS_MAP['assigned'];
}

const TABS = [
  { key: 'active',  label: '📦 Mera Load' },
  { key: 'history', label: '📋 Purana Record' },
];

const C = {
  bg:'#f1f5f9', card:'#ffffff', border:'#e2e8f0', text:'#0f172a',
  sub:'#475569', muted:'#94a3b8', teal:'#0d9488', tealDk:'#0f766e',
  tealGlow:'rgba(13,148,136,0.12)', green:'#10b981', greenGlow:'rgba(16,185,129,0.12)',
  amber:'#f59e0b', blue:'#3b82f6', red:'#ef4444',
  shadow:'0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
  shadowMd:'0 4px 12px rgba(0,0,0,0.08)', shadowLg:'0 10px 25px rgba(0,0,0,0.1)',
};

// ═══════════════════════════════════════════════════════════════════════════════
export default function DriverPanel() {
  const { user, logout }               = useAuth();
  const [shipments, setShipments]      = useState([]);
  const [loading, setLoading]          = useState(true);
  const [error, setError]              = useState(null);
  const [tab, setTab]                  = useState('active');
  // Upload state
  const [uploadTarget, setUploadTarget]= useState(null);
  const [photos, setPhotos]            = useState([null, null, null]);
  const [previews, setPreviews]        = useState([null, null, null]);
  const [uploading, setUploading]      = useState(false);
  const [successMsg, setSuccessMsg]    = useState('');
  // POD preview state
  const [podPreview, setPodPreview]    = useState(null);  // { shipment_id, images, ... }
  const [podLoading, setPodLoading]    = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await fetchDriverShipments();
      setShipments(Array.isArray(data) ? data : (data.results || []));
    } catch (e) { setError(e.message); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const active  = shipments.filter(s => s.pod_status !== 'Uploaded');
  const history = shipments.filter(s => s.pod_status === 'Uploaded');
  const displayed = tab === 'active' ? active : history;

  // Photo handlers
  function handlePhotoSelect(i, file) {
    const np=[...photos], nv=[...previews];
    np[i]=file; nv[i]=file?URL.createObjectURL(file):null;
    setPhotos(np); setPreviews(nv);
  }
  function clearPhotos() {
    previews.forEach(p=>p&&URL.revokeObjectURL(p));
    setPhotos([null,null,null]); setPreviews([null,null,null]);
  }
  function openUploadModal(s) { clearPhotos(); setUploadTarget(s); setSuccessMsg(''); }
  function closeUploadModal() { clearPhotos(); setUploadTarget(null); }

  async function handleSubmit() {
    if (!uploadTarget) return;
    if (!photos[0]&&!photos[1]&&!photos[2]) { alert('Kam se kam 1 photo to daalo!'); return; }
    setUploading(true);
    try {
      await uploadPodImages(uploadTarget.id, photos);
      setSuccessMsg('✅ Photo upload ho gaya! Manager ko notification chala gaya.');
      closeUploadModal();
      load();
      setTimeout(()=>setSuccessMsg(''),5000);
    } catch(e) { alert('Upload fail: '+(e.message||'Kuch gadbad ho gayi')); }
    setUploading(false);
  }

  // POD Preview — fetch image URLs and show modal
  async function openPodPreview(shipmentId) {
    setPodLoading(true);
    try {
      const data = await viewPod(shipmentId);
      setPodPreview(data);
    } catch(e) { alert('POD load nahi hua: '+e.message); }
    setPodLoading(false);
  }

  // Invoice View — open in new tab
  function openInvoice(shipmentId) {
    window.open(getInvoiceUrl(shipmentId), '_blank');
  }

  // Delete POD — clear images and re-upload
  async function handleDeletePod(id) {
    if (!id) { alert('Shipment ID missing!'); return; }
    if (!window.confirm('Kya aap sach mein ye photo delete karna chahte hain?')) return;
    try {
      console.log('Deleting POD for:', id);
      const res = await deletePod(id);
      setSuccessMsg(`✅ ${res.message}`);
      setPodPreview(null);
      load();
      setTimeout(()=>setSuccessMsg(''), 5000);
    } catch(e) {
      alert('Delete fail: '+e.message);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <div style={{ minHeight:'100vh', background:C.bg, fontFamily:"'Inter','Segoe UI',sans-serif" }}>

      {/* Header */}
      <header style={{
        background:C.card, borderBottom:`1px solid ${C.border}`,
        padding:'0.9rem 1.25rem', display:'flex', alignItems:'center',
        justifyContent:'space-between', position:'sticky', top:0, zIndex:100, boxShadow:C.shadow,
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:'0.75rem' }}>
          <img src="/manncj.png" alt="CJ Darcl"
            onError={e=>{e.currentTarget.style.display='none';}}
            style={{ height:'38px', objectFit:'contain' }} />
          <div style={{ width:'1px', height:'30px', background:C.border }} />
          <div>
            <div style={{ fontWeight:900, fontSize:'1.2rem', color:C.text }}>🚚 Driver Panel</div>
            <div style={{ fontSize:'0.72rem', color:C.muted, fontWeight:500 }}>
              {user?.full_name||user?.username}
              {user?.profile?.vehicle_no && (
                <span> · Gaadi: <span style={{color:C.teal,fontWeight:700}}>{user.profile.vehicle_no}</span></span>
              )}
            </div>
          </div>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:'0.6rem' }}>
          <NotificationBell />
          <button onClick={logout} style={{
            padding:'0.45rem 0.9rem', background:'transparent',
            border:`1px solid ${C.border}`, borderRadius:'7px',
            color:C.sub, cursor:'pointer', fontSize:'0.78rem', fontWeight:600, fontFamily:'inherit',
          }}>Bahar Jao</button>
        </div>
      </header>

      {/* Body */}
      <div style={{ maxWidth:'700px', margin:'0 auto', padding:'1.25rem 1rem' }}>

        {/* Welcome */}
        <div style={{
          background:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
          borderRadius:'14px', padding:'1.3rem 1.5rem', marginBottom:'1.25rem',
          color:'#fff', boxShadow:`0 4px 14px ${C.teal}35`,
        }}>
          <div style={{ fontSize:'1.3rem', fontWeight:900 }}>
            🙏 Namaste, {user?.full_name||user?.username}!
          </div>
          <div style={{ fontSize:'0.85rem', opacity:0.85, marginTop:'0.3rem' }}>
            Aapke paas <strong>{active.length}</strong> load baaki hai · <strong>{history.length}</strong> deliver ho chuke
          </div>
        </div>

        {/* Stats */}
        <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:'0.75rem', marginBottom:'1.25rem' }}>
          <MiniStat icon="📦" value={shipments.length} label="Kul Load"  color={C.teal} />
          <MiniStat icon="⏳" value={active.length}    label="Baaki Hai" color={C.amber} />
          <MiniStat icon="✅" value={history.length}   label="Ho Gaya"   color={C.green} />
        </div>

        {/* Success */}
        {successMsg && (
          <div style={{
            background:C.greenGlow, border:`1px solid ${C.green}40`,
            borderRadius:'10px', padding:'0.85rem 1rem',
            color:C.green, fontWeight:700, fontSize:'0.9rem',
            marginBottom:'1rem', textAlign:'center',
          }}>{successMsg}</div>
        )}

        {/* Tabs */}
        <div style={{
          display:'grid', gridTemplateColumns:'1fr 1fr',
          background:C.card, borderRadius:'10px', padding:'4px',
          border:`1px solid ${C.border}`, marginBottom:'1rem', gap:'4px',
        }}>
          {TABS.map(t=>(
            <button key={t.key} onClick={()=>setTab(t.key)} style={{
              padding:'0.65rem', borderRadius:'8px', border:'none',
              background:tab===t.key?C.tealGlow:'transparent',
              color:tab===t.key?C.teal:C.muted,
              fontWeight:700, fontSize:'0.88rem', cursor:'pointer', fontFamily:'inherit',
              boxShadow:tab===t.key?`0 0 0 1px ${C.teal}30`:'none',
            }}>{t.label}</button>
          ))}
        </div>

        {/* Refresh */}
        <div style={{ display:'flex', justifyContent:'flex-end', marginBottom:'0.75rem' }}>
          <button onClick={load} style={{
            padding:'0.4rem 0.85rem', background:`${C.teal}10`,
            border:`1px solid ${C.teal}40`, borderRadius:'7px',
            color:C.teal, fontWeight:700, cursor:'pointer', fontSize:'0.8rem', fontFamily:'inherit',
          }}>↻ Dubara Dekho</button>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background:'#FEF2F2', border:`1px solid ${C.red}30`, borderRadius:'10px',
            padding:'0.75rem 1rem', color:'#B91C1C', fontSize:'0.85rem', marginBottom:'1rem',
          }}>⚠️ {error}</div>
        )}

        {/* Loading / Empty / Cards */}
        {loading ? (
          <div style={{ textAlign:'center', padding:'3rem', color:C.muted }}>
            <div style={{ fontSize:'2.5rem', marginBottom:'0.5rem' }}>⏳</div>
            <div>Load list aa rahi hai...</div>
          </div>
        ) : displayed.length===0 ? (
          <div style={{
            textAlign:'center', padding:'3rem',
            background:C.card, borderRadius:'14px', border:`1px solid ${C.border}`,
          }}>
            <div style={{ fontSize:'2.5rem', marginBottom:'0.5rem' }}>{tab==='active'?'🚫':'📋'}</div>
            <div style={{ fontWeight:700, color:C.text }}>
              {tab==='active'?'Koi load nahi mila':'Abhi koi purana record nahi'}
            </div>
          </div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', gap:'0.85rem' }}>
            {displayed.map(s=>(
              <ShipmentCard key={s.id} s={s}
                onUpload={()=>openUploadModal(s)}
                onViewPod={()=>openPodPreview(s.shipment_id)}
                onViewInvoice={()=>openInvoice(s.shipment_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {uploadTarget && (
        <UploadModal shipment={uploadTarget} photos={photos} previews={previews}
          uploading={uploading} onPhotoSelect={handlePhotoSelect}
          onSubmit={handleSubmit} onClose={closeUploadModal} />
      )}

      {/* POD Preview Modal */}
      {(podPreview || podLoading) && (
        <PodPreviewModal data={podPreview} loading={podLoading}
          onDelete={(id) => handleDeletePod(id)}
          onClose={()=>{setPodPreview(null);setPodLoading(false);}} />
      )}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
// SHIPMENT CARD
// ═══════════════════════════════════════════════════════════════════════════════
function ShipmentCard({ s, onUpload, onViewPod, onViewInvoice }) {
  const st = getStatus(s);
  const podDone = s.pod_status === 'Uploaded';

  return (
    <div style={{
      background:C.card, border:`1px solid ${C.border}`,
      borderRadius:'14px', overflow:'hidden', boxShadow:C.shadow,
      transition:'box-shadow 0.2s, transform 0.2s',
    }}
      onMouseEnter={e=>{e.currentTarget.style.boxShadow=C.shadowMd;e.currentTarget.style.transform='translateY(-2px)';}}
      onMouseLeave={e=>{e.currentTarget.style.boxShadow=C.shadow;e.currentTarget.style.transform='translateY(0)';}}
    >
      {/* Top: CN + Status */}
      <div style={{
        background:st.bg, borderBottom:`1px solid ${st.color}20`,
        padding:'0.7rem 1.15rem', display:'flex', justifyContent:'space-between', alignItems:'center',
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:'0.5rem' }}>
          <span style={{ fontSize:'1.1rem' }}>{st.icon}</span>
          <span style={{ fontWeight:800, fontSize:'1rem', color:C.text, fontFamily:'monospace' }}>{s.shipment_id}</span>
        </div>
        <span style={{
          padding:'0.2rem 0.7rem', borderRadius:'999px', fontSize:'0.72rem',
          fontWeight:700, background:`${st.color}15`, color:st.color, border:`1px solid ${st.color}30`,
        }}>{st.label}</span>
      </div>

      {/* Details */}
      <div style={{ padding:'0.85rem 1.15rem' }}>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0.6rem 1.25rem' }}>
          <DetailItem icon="📍" label="Kahan Se"       value={s.origin||'—'} />
          <DetailItem icon="🏁" label="Kahan Tak"      value={s.destination||'—'} />
          <DetailItem icon="🚛" label="Gaadi No."      value={s.vehicle_no||'N/A'} />
          <DetailItem icon="📅" label="Bhejne Ki Date" value={s.dispatch_date||'—'} />
        </div>
      </div>

      {/* Actions */}
      <div style={{ borderTop:`1px solid ${C.border}`, padding:'0.7rem 1.15rem', background:'#fafbfc' }}>
        {podDone ? (
          <div>
            <div style={{
              display:'flex', alignItems:'center', gap:'0.5rem',
              color:C.green, fontWeight:700, fontSize:'0.88rem', marginBottom:'0.6rem',
            }}>
              ✅ Upload ho gaya
              {s.pod_uploaded_at && (
                <span style={{ color:C.muted, fontWeight:500, fontSize:'0.72rem' }}>
                  · {new Date(s.pod_uploaded_at).toLocaleDateString('en-IN')}
                </span>
              )}
            </div>
            {/* Single button: View POD (Note: Invoice removed as per user request) */}
            <div style={{ display:'grid', gridTemplateColumns:'1fr', gap:'0.5rem' }}>
              <button onClick={onViewPod} style={{
                padding:'0.65rem', background:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
                color:'#fff', border:'none', borderRadius:'9px',
                fontWeight:700, fontSize:'0.9rem', cursor:'pointer', fontFamily:'inherit',
                boxShadow:`0 3px 10px ${C.teal}30`,
              }}>📸 POD Dekho</button>
            </div>
          </div>
        ) : (
          <button onClick={onUpload} style={{
            width:'100%', padding:'0.75rem',
            background:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
            color:'#fff', border:'none', borderRadius:'10px',
            fontWeight:700, fontSize:'0.95rem', cursor:'pointer', fontFamily:'inherit',
            boxShadow:`0 3px 10px ${C.teal}30`,
          }}
            onMouseDown={e=>{e.currentTarget.style.transform='scale(0.98)';}}
            onMouseUp={e=>{e.currentTarget.style.transform='scale(1)';}}
          >📸 Photo Bhejo</button>
        )}
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
// POD PREVIEW MODAL — Shows uploaded images in a gallery
// ═══════════════════════════════════════════════════════════════════════════════
function PodPreviewModal({ data, loading, onDelete, onClose }) {
  return (
    <div style={{
      position:'fixed', inset:0, background:'rgba(0,0,0,0.6)',
      backdropFilter:'blur(6px)', display:'flex', alignItems:'center',
      justifyContent:'center', zIndex:1000, padding:'1rem',
    }} onClick={e=>{if(e.target===e.currentTarget)onClose();}}>
      <div style={{
        background:C.card, borderRadius:'18px', width:'100%', maxWidth:'520px',
        maxHeight:'90vh', overflow:'auto', boxShadow:C.shadowLg,
      }}>
        {/* Header */}
        <div style={{
          background:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
          padding:'1.1rem 1.25rem', color:'#fff',
          display:'flex', justifyContent:'space-between', alignItems:'center',
        }}>
          <div>
            <div style={{ fontWeight:900, fontSize:'1.1rem' }}>📸 POD Photos</div>
            {data && (
              <div style={{ fontSize:'0.78rem', opacity:0.85, marginTop:'0.15rem' }}>
                {data.shipment_id} · {data.origin} → {data.destination}
              </div>
            )}
          </div>
          <div style={{ display:'flex', gap:'0.5rem' }}>
            {data && (
              <button 
                id="delete-pod-btn"
                onClick={() => onDelete(data.id || data.shipment_id)} 
                style={{
                  background:'rgba(244,63,94,0.2)', border:'1px solid rgba(244,63,94,0.5)',
                  color:'#fff', borderRadius:'8px', padding:'0.4rem 0.75rem',
                  fontSize:'0.75rem', fontWeight:700, cursor:'pointer',
                }}>🗑️ Hatao</button>
            )}
            <button onClick={onClose} style={{
              background:'rgba(255,255,255,0.2)', border:'none', color:'#fff',
              borderRadius:'50%', width:'32px', height:'32px', cursor:'pointer',
              fontSize:'1rem', display:'flex', alignItems:'center', justifyContent:'center',
            }}>✕</button>
          </div>
        </div>

        {/* Content */}
        <div style={{ padding:'1.25rem' }}>
          {loading ? (
            <div style={{ textAlign:'center', padding:'2rem', color:C.muted }}>
              <div style={{ fontSize:'2rem', marginBottom:'0.5rem' }}>⏳</div>
              <div>Photos load ho rahe hain...</div>
            </div>
          ) : !data || data.images.length === 0 ? (
            <div style={{ textAlign:'center', padding:'2rem', color:C.muted }}>
              <div style={{ fontSize:'2rem', marginBottom:'0.5rem' }}>🚫</div>
              <div>Koi photo nahi mili</div>
            </div>
          ) : (
            <div style={{ display:'flex', flexDirection:'column', gap:'1rem' }}>
              {/* Shipment info bar */}
              <div style={{
                display:'grid', gridTemplateColumns:'1fr 1fr',
                gap:'0.5rem', padding:'0.75rem',
                background:'#f8fafc', borderRadius:'10px',
                border:`1px solid ${C.border}`,
              }}>
                <div>
                  <div style={{ fontSize:'0.6rem', color:C.muted, fontWeight:700, textTransform:'uppercase' }}>GAADI</div>
                  <div style={{ fontSize:'0.85rem', fontWeight:600, color:C.text }}>{data.vehicle_no||'—'}</div>
                </div>
                <div>
                  <div style={{ fontSize:'0.6rem', color:C.muted, fontWeight:700, textTransform:'uppercase' }}>DATE</div>
                  <div style={{ fontSize:'0.85rem', fontWeight:600, color:C.text }}>{data.dispatch_date||'—'}</div>
                </div>
              </div>

              {/* Images */}
              {data.images.map((img, idx) => (
                <div key={idx}>
                  <div style={{
                    fontSize:'0.72rem', fontWeight:700, color:C.sub,
                    textTransform:'uppercase', marginBottom:'0.35rem',
                  }}>
                    📷 Photo {img.index}
                  </div>
                  <div style={{
                    borderRadius:'12px', overflow:'hidden',
                    border:`2px solid ${C.teal}30`,
                    boxShadow:C.shadow,
                  }}>
                    <img
                      src={img.url}
                      alt={`POD Photo ${img.index}`}
                      style={{
                        width:'100%', maxHeight:'300px',
                        objectFit:'contain', display:'block',
                        background:'#f1f5f9',
                      }}
                    />
                  </div>
                </div>
              ))}

              {/* Upload info */}
              {data.pod_uploaded_at && (
                <div style={{
                  textAlign:'center', fontSize:'0.75rem', color:C.muted,
                  padding:'0.5rem', background:'#f8fafc', borderRadius:'8px',
                }}>
                  📅 Upload kiya: {new Date(data.pod_uploaded_at).toLocaleString('en-IN')}
                </div>
              )}
            </div>
          )}

          {/* Close button */}
          <button onClick={onClose} style={{
            width:'100%', padding:'0.75rem', marginTop:'1rem',
            background:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
            color:'#fff', border:'none', borderRadius:'10px',
            fontWeight:700, fontSize:'0.9rem', cursor:'pointer', fontFamily:'inherit',
          }}>Band Karo</button>
        </div>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
// UPLOAD MODAL
// ═══════════════════════════════════════════════════════════════════════════════
function UploadModal({ shipment, photos, previews, uploading, onPhotoSelect, onSubmit, onClose }) {
  const labels = ['Photo 1 (zaruri)', 'Photo 2 (agar ho)', 'Photo 3 (agar ho)'];
  return (
    <div style={{
      position:'fixed', inset:0, background:'rgba(0,0,0,0.5)',
      backdropFilter:'blur(4px)', display:'flex', alignItems:'center',
      justifyContent:'center', zIndex:1000, padding:'1rem',
    }} onClick={e=>{if(e.target===e.currentTarget)onClose();}}>
      <div style={{
        background:C.card, borderRadius:'18px', width:'100%', maxWidth:'440px',
        boxShadow:C.shadowLg, overflow:'hidden',
      }}>
        <div style={{
          background:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
          padding:'1.1rem 1.25rem', color:'#fff',
        }}>
          <div style={{ fontWeight:900, fontSize:'1.1rem' }}>📸 Photo Bhejo</div>
          <div style={{ fontSize:'0.78rem', opacity:0.85, marginTop:'0.15rem' }}>
            {shipment.shipment_id} · {shipment.origin} → {shipment.destination}
          </div>
          <div style={{ fontSize:'0.7rem', opacity:0.7, marginTop:'0.2rem' }}>
            ⚡ Photo bhejte hi manager ko notification jayega
          </div>
        </div>
        <div style={{ padding:'1.25rem' }}>
          <div style={{ display:'flex', flexDirection:'column', gap:'0.85rem' }}>
            {labels.map((label, i) => (
              <div key={i}>
                <div style={{
                  fontSize:'0.75rem', fontWeight:700, color:C.sub,
                  textTransform:'uppercase', marginBottom:'0.35rem',
                }}>{label}</div>
                {previews[i] ? (
                  <div style={{
                    position:'relative', borderRadius:'10px', overflow:'hidden',
                    border:`2px solid ${C.teal}40`,
                  }}>
                    <img src={previews[i]} alt={`POD ${i+1}`}
                      style={{ width:'100%', height:'120px', objectFit:'cover', display:'block' }} />
                    <button onClick={()=>onPhotoSelect(i,null)} style={{
                      position:'absolute', top:'6px', right:'6px',
                      background:'rgba(0,0,0,0.6)', color:'#fff', border:'none',
                      borderRadius:'50%', width:'26px', height:'26px', cursor:'pointer',
                      fontSize:'0.8rem', display:'flex', alignItems:'center', justifyContent:'center',
                    }}>✕</button>
                  </div>
                ) : (
                  <label style={{
                    display:'flex', alignItems:'center', justifyContent:'center', gap:'0.5rem',
                    padding:'1.1rem', border:`2px dashed ${C.border}`, borderRadius:'10px',
                    cursor:'pointer', background:'#f8fafc', color:C.muted,
                    fontSize:'0.88rem', fontWeight:600,
                  }}
                    onMouseEnter={e=>{e.currentTarget.style.borderColor=C.teal;e.currentTarget.style.background=C.tealGlow;}}
                    onMouseLeave={e=>{e.currentTarget.style.borderColor=C.border;e.currentTarget.style.background='#f8fafc';}}
                  >
                    📷 {i===0?'Photo choose karo':'Photo daalo (optional)'}
                    <input type="file" accept="image/*" capture="environment"
                      onChange={e=>{if(e.target.files[0])onPhotoSelect(i,e.target.files[0]);e.target.value='';}}
                      style={{ display:'none' }} />
                  </label>
                )}
              </div>
            ))}
          </div>
          <div style={{ display:'flex', gap:'0.75rem', marginTop:'1.25rem' }}>
            <button onClick={onSubmit} disabled={uploading} style={{
              flex:1, padding:'0.8rem',
              background:uploading?C.muted:`linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
              color:'#fff', border:'none', borderRadius:'10px',
              fontWeight:700, fontSize:'0.95rem',
              cursor:uploading?'not-allowed':'pointer', fontFamily:'inherit',
            }}>
              {uploading?'⏳ Bhej rahe hain...':'✅ Bhej Do'}
            </button>
            <button onClick={onClose} disabled={uploading} style={{
              padding:'0.8rem 1.1rem', background:'#f1f5f9',
              border:`1px solid ${C.border}`, borderRadius:'10px',
              color:C.sub, fontWeight:600, fontSize:'0.9rem', cursor:'pointer', fontFamily:'inherit',
            }}>Band Karo</button>
          </div>
        </div>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════════
function MiniStat({ icon, value, label, color }) {
  return (
    <div style={{
      background:C.card, border:`1px solid ${C.border}`, borderRadius:'12px',
      padding:'0.85rem 0.75rem', textAlign:'center',
      borderTop:`3px solid ${color}`, boxShadow:C.shadow,
    }}>
      <div style={{ fontSize:'1.1rem', marginBottom:'0.2rem' }}>{icon}</div>
      <div style={{ fontSize:'1.6rem', fontWeight:800, color, lineHeight:1 }}>{value}</div>
      <div style={{
        fontSize:'0.68rem', color:C.muted, fontWeight:700,
        textTransform:'uppercase', letterSpacing:'0.05em', marginTop:'0.2rem',
      }}>{label}</div>
    </div>
  );
}

function DetailItem({ icon, label, value }) {
  return (
    <div>
      <div style={{
        fontSize:'0.65rem', color:C.muted, fontWeight:700,
        textTransform:'uppercase', letterSpacing:'0.04em',
      }}>{icon} {label}</div>
      <div style={{ fontSize:'0.9rem', color:C.text, fontWeight:600, marginTop:'0.1rem' }}>{value}</div>
    </div>
  );
}
