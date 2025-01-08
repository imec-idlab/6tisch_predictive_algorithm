/*
 * Copyright (c) 2013, Institute for Pervasive Computing, ETH Zurich
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the Institute nor the names of its contributors
 *    may be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE INSTITUTE AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE INSTITUTE OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 *
 * This file is part of the Contiki operating system.
 */

/**
 * \file
 *      CoAP Engine
 * \author
 *      Matthias Kovatsch <kovatsch@inf.ethz.ch>
 *      Dries Van Leemput <dries.vanleemput@ugent.be>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "contiki.h"
#include "coap-engine.h"
#include "net/routing/routing.h"
#include "net/netstack.h"
#include "sys/log.h"
#include "net/ipv6/uip-debug.h"
#include "rpl-dag-root.h"
#include "rpl.h"
#include "sys/energest.h"

/* Log configuration */
#include "sys/log.h"
#define LOG_MODULE "App"
#define LOG_LEVEL LOG_LEVEL_APP
#define PRED_DELAY        (5 * 60 * CLOCK_SECOND)
#define PRED_INTERVAL     (10 * CLOCK_SECOND)
/*
 * Resources to be activated need to be imported through the extern keyword.
 * The build system automatically compiles the resources in the corresponding sub-directory.
 */
extern coap_resource_t  res_seqno;

PROCESS(coap_server, "CoAP Server");
AUTOSTART_PROCESSES(&coap_server);

static unsigned long
to_mseconds(uint64_t time)
{
  return (unsigned long)(time*1000 / ENERGEST_SECOND);
}

PROCESS_THREAD(coap_server, ev, data)
{
  PROCESS_BEGIN();

  NETSTACK_ROUTING.root_start();
  NETSTACK_MAC.on();

  PROCESS_PAUSE();

  LOG_INFO("Starting Erbium Example Server\n");
  coap_activate_resource(&res_seqno, "test/seqno");

  static struct etimer et;
  etimer_set(&et, PRED_DELAY);

  while(1) {
    PROCESS_YIELD();
    if(etimer_expired(&et)){
      rpl_dag_root_print_links("");
      LOG_INFO("PREDICT %lu ms, RX %lu ms, TX %lu ms\n", clock_time(),to_mseconds(energest_type_time(ENERGEST_TYPE_LISTEN)),
            to_mseconds(energest_type_time(ENERGEST_TYPE_TRANSMIT)));
      etimer_set(&et, PRED_INTERVAL);
    }
  }

  PROCESS_END();
}
